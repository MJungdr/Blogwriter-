from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import os
import re
from datetime import date
from io import BytesIO
from typing import Any, Dict
from urllib.parse import quote

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, PrivateAttr
import yaml
from google import genai

from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from crewai_tools import SerperDevTool

from .editorial_prompts import (
    AUDIENCE_AND_STYLE,
    EDITORIAL_QUALITY_CHECK,
    PLANNING_RULES,
    SOURCING_AND_SAFETY,
    WRITING_RULES,
)


logger = logging.getLogger(__name__)

MAX_RESEARCH_CHARS = 24_000
LLM_EMPTY_RESPONSE_RETRIES = 2


def show_progress(message: str) -> None:
    """Write safe execution progress to the backend terminal immediately."""
    print(f"[BlogGPT] {message}", flush=True)


def show_task_completion(output: Any) -> None:
    """Report task completion without exposing prompts or private reasoning."""
    agent_name = getattr(output, "agent", None) or "Agent"
    show_progress(f"Completed: {agent_name}")


# Simple config loader (YAML + env overrides)
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    load_dotenv()  # Load .env from current or parent dirs
    load_dotenv(find_dotenv(), override=False)

    config = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Defaults with overrides
    app_cfg = config.get("app", {})
    llm_cfg = config.get("llm", {})
    crew_cfg = config.get("crew", {})

    # Required env validation
    missing = []
    if not os.getenv("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    llm_model = llm_cfg.get("model", "openai/gpt-5.6-luna")
    if llm_model.startswith("openai/") and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    search_provider = os.getenv("SEARCH_PROVIDER", config.get("search", {}).get("provider", "auto")).lower()
    if search_provider not in {"auto", "serper", "gemini"}:
        raise RuntimeError("SEARCH_PROVIDER must be one of: auto, serper, gemini")
    if search_provider == "serper" and not os.getenv("SERPER_API_KEY"):
        missing.append("SERPER_API_KEY")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    return {
        "host": app_cfg.get("host", "127.0.0.1"),
        "port": app_cfg.get("port", 8002),
        "cors_origins": app_cfg.get("cors_origins", ["http://localhost:3000", "http://127.0.0.1:3000"]),
        "cors_origin_regex": app_cfg.get(
            "cors_origin_regex",
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        ),
        "llm_model": llm_model,
        "crew_verbose": crew_cfg.get("verbose", True),
        "search_provider": search_provider,
        "search_model": config.get("search", {}).get("model", "gemini-3.5-flash"),
    }


# FastAPI app
app = FastAPI()

# Load config early
settings = load_config()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["cors_origins"],
    allow_origin_regex=settings["cors_origin_regex"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TopicRequest(BaseModel):
    topic: str


class DocumentRequest(BaseModel):
    topic: str
    content: str
    image_data_url: str | None = None


class SearchInput(BaseModel):
    search_query: str = Field(
        ...,
        description=(
            "One search query. Pass exactly one key-value object per tool call, for example "
            '{"search_query": "AI research tools"}. Never pass a list of queries.'
        ),
    )


def validate_planner_output(task_output):
    """Reject tool-format apologies that are not usable research plans."""
    output = task_output.raw.strip()
    normalized = output.lower()
    invalid_final_answer_markers = (
        "action input",
        "valid key, value dictionary",
        "must pass a simple json object",
        "let me correct the input format",
        "let me search again",
    )
    if any(marker in normalized for marker in invalid_final_answer_markers):
        return (
            False,
            "Do not return an explanation about tool input as the final answer. Use the Search the internet "
            "tool before finalizing. Call it once per query with exactly one object such as "
            '{"search_query": "research topic"}, then return the requested content plan with sources.',
        )
    return True, output


def validate_article_references(article: str) -> tuple[bool, str]:
    """Check the minimum citation contract before an article leaves the API."""
    references_match = re.search(r"(?im)^##\s+references\s*$", article)
    if not references_match:
        return False, "missing a level-two References section"

    body = article[: references_match.start()]
    references = article[references_match.end() :]
    link_pattern = re.compile(r"\[[^]]+\]\((https?://[^)]+)\)")
    inline_urls = set(link_pattern.findall(body))
    reference_urls = set(link_pattern.findall(references))
    if not inline_urls:
        return False, "missing inline Markdown citations"
    if not reference_urls:
        return False, "References contains no clickable source links"

    missing_from_references = inline_urls - reference_urls
    if missing_from_references:
        return False, "one or more inline citations are absent from References"
    return True, ""


def gemini_api_model_name(model: str) -> str:
    if model.startswith("gemini/"):
        return model.split("/", 1)[1]
    return model


class AutoSearchTool(BaseTool):
    name: str = "Search the internet"
    description: str = (
        "Searches the internet for one query at a time. Call this tool separately for each query and "
        "pass a single object with the search_query key; never pass a list of query objects. In auto "
        "mode it tries Serper first, then falls back to Gemini Google Search grounding if Serper is "
        "unavailable or unauthorized."
    )
    args_schema: type[BaseModel] = SearchInput
    provider: str = "auto"
    gemini_model: str = "gemini-3.5-flash"
    _serper_tool: SerperDevTool | None = PrivateAttr(default=None)
    _serper_disabled: bool = PrivateAttr(default=False)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.provider in {"auto", "serper"} and os.getenv("SERPER_API_KEY"):
            os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY", "")
            self._serper_tool = SerperDevTool()

    def _run(self, search_query: str, **_: Any) -> str:
        if self.provider in {"auto", "serper"} and self._serper_tool and not self._serper_disabled:
            try:
                result = self._serper_tool._run(search_query=search_query)
                result_text = str(result)
                if self.provider == "auto" and self._is_search_error(result_text):
                    logger.warning("Serper returned an unusable response; falling back to Gemini Google Search")
                else:
                    return result_text
            except Exception as exc:
                if self.provider == "serper":
                    raise
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in {401, 403}:
                    self._serper_disabled = True
                    logger.warning(
                        "Serper authentication was rejected; Gemini Google Search will be used for future requests"
                    )
                logger.warning("Serper search failed; falling back to Gemini Google Search: %s", exc)
        elif self.provider == "serper":
            raise RuntimeError("SERPER_API_KEY is required when SEARCH_PROVIDER=serper")

        return self._run_gemini_search(search_query)

    @staticmethod
    def _is_search_error(result: str) -> bool:
        normalized = result.lower()
        error_markers = (
            "unauthorized",
            "forbidden",
            "invalid api key",
            "quota exceeded",
            "rate limit",
            "too many requests",
            "payment required",
            "credits exhausted",
        )
        return not result.strip() or any(marker in normalized for marker in error_markers)

    def _run_gemini_search(self, search_query: str) -> str:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        interaction = client.interactions.create(
            model=gemini_api_model_name(self.gemini_model),
            input=(
                "Search the web and return a concise, source-grounded research summary for this query. "
                "Include important facts, dates, and useful source URLs when available.\n\n"
                f"Query: {search_query}"
            ),
            tools=[{"type": "google_search"}],
        )
        output = getattr(interaction, "output_text", None)
        if output:
            return output
        return str(interaction)


def add_hyperlink(paragraph: Paragraph, label: str, url: str) -> None:
    """Add a clickable external hyperlink to a python-docx paragraph."""
    relationship_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
        relationship_id,
    )
    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "0563C1")
    underline = OxmlElement("w:u")
    underline.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "single")
    run_properties.extend((color, underline))
    run.append(run_properties)
    text_element = OxmlElement("w:t")
    text_element.text = label
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_markdown_runs(paragraph: Paragraph, text: str) -> None:
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    parts = re.split(
        r"(\[[^]]+\]\(https?://[^)]+\)|\*\*.+?\*\*|__.+?__|(?<!\*)\*[^*]+?\*(?!\*))",
        text,
    )
    for part in parts:
        if not part:
            continue
        link_match = re.fullmatch(r"\[([^]]+)\]\((https?://[^)]+)\)", part)
        if link_match:
            add_hyperlink(paragraph, link_match.group(1), link_match.group(2))
        elif (part.startswith("**") and part.endswith("**")) or (
            part.startswith("__") and part.endswith("__")
        ):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            paragraph.add_run(part.replace("`", ""))


def build_article_docx(request: DocumentRequest) -> BytesIO:
    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1

    heading_tokens = {
        "Heading 1": (16, "2E74B5", 16, 8),
        "Heading 2": (13, "2E74B5", 12, 6),
        "Heading 3": (12, "1F4D78", 8, 4),
    }
    for style_name, (size, color, before, after) in heading_tokens.items():
        style = styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    for style_name in ("List Bullet", "List Number"):
        style = styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.5)
        style.paragraph_format.first_line_indent = Inches(-0.25)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.line_spacing = 1.167

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(14)
    title_run = title.add_run(request.topic.strip() or "Generated Article")
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(24)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor.from_string("0B2545")

    if request.image_data_url and request.image_data_url.startswith("data:image/"):
        try:
            _, encoded = request.image_data_url.split(",", 1)
            document.add_picture(BytesIO(base64.b64decode(encoded)), width=Inches(6.5))
            document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except (ValueError, binascii.Error):
            logger.warning("Skipping invalid article image data")

    for raw_line in request.content.splitlines():
        line = raw_line.strip()
        if not line or line in {"---", "***", "___"}:
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        bullet_match = re.match(r"^[-*+]\s+(.+)$", line)
        number_match = re.match(r"^\d+[.)]\s+(.+)$", line)

        if heading_match:
            paragraph = document.add_paragraph(style=f"Heading {len(heading_match.group(1))}")
            add_markdown_runs(paragraph, heading_match.group(2))
        elif bullet_match:
            paragraph = document.add_paragraph(style="List Bullet")
            add_markdown_runs(paragraph, bullet_match.group(1))
        elif number_match:
            paragraph = document.add_paragraph(style="List Number")
            add_markdown_runs(paragraph, number_match.group(1))
        else:
            paragraph = document.add_paragraph()
            add_markdown_runs(paragraph, line)

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output


def generate_topic_image(topic: str) -> str:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    interaction = client.interactions.create(
        model="gemini-3.1-flash-image",
        input=(
            "Create a polished, editorial-quality 16:9 hero image for a blog "
            f"article about: {topic}. Do not include logos, watermarks, or text."
        ),
        response_format={
            "type": "image",
            "mime_type": "image/jpeg",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )
    image = interaction.output_image
    if image is None or not image.data:
        raise RuntimeError("Gemini returned no generated image")

    encoded = image.data
    if isinstance(encoded, bytes):
        encoded = base64.b64encode(encoded).decode("ascii")
    return f"{image.mime_type or 'image/jpeg'};base64,{encoded}"


# Crew builder (unchanged from notebook)
def build_crew() -> Crew:
    llm_api_key = (
        os.getenv("OPENAI_API_KEY")
        if settings["llm_model"].startswith("openai/")
        else os.getenv("GOOGLE_API_KEY")
    )
    llm = LLM(
        api_key=llm_api_key,
        model=settings["llm_model"],
    )
    # CrewAI's Gemini native function-calling path can return an empty text response
    # after a tool call because the agent executor uses its own ReAct tool loop.
    # Keep tool execution in that loop so each observation is fed back to the model.
    if settings["llm_model"].startswith("gemini/") and hasattr(llm, "supports_tools"):
        llm.supports_tools = False

    planner = Agent(
        role="Content Planner",
        goal="Plan a focused, practical, evidence-based WordPress article on {topic}",
        backstory=(
            "You plan English articles for BlogGPT's AI & Research category. Your work is the basis for the "
            "Content Writer.\n\n"
            f"{AUDIENCE_AND_STYLE}\n\n{SOURCING_AND_SAFETY}"
        ),
        allow_delegation=False,
        verbose=settings["crew_verbose"],
        llm=llm,
    )

    writer = Agent(
        role="Content Writer",
        goal="Write a practical, readable, source-grounded WordPress article about {topic}",
        backstory=(
            "You write English articles for BlogGPT's AI & Research category. You help researchers turn a "
            "concept into a workflow they can understand, assess, and try.\n\n"
            f"{AUDIENCE_AND_STYLE}\n\n{SOURCING_AND_SAFETY}\n\n{WRITING_RULES}"
        ),
        allow_delegation=False,
        verbose=settings["crew_verbose"],
        llm=llm,
    )

    editor = Agent(
        role="Editor",
        goal=(
            "Edit a BlogGPT WordPress article for practical clarity, scientific care, and reader usefulness."
        ),
        backstory=(
            "You are a rigorous but reader-centred editor for an AI & Research blog.\n\n"
            f"{AUDIENCE_AND_STYLE}\n\n{SOURCING_AND_SAFETY}\n\n{EDITORIAL_QUALITY_CHECK}"
        ),
        allow_delegation=False,
        verbose=settings["crew_verbose"],
        llm=llm,
    )

    plan_task = Task(
        description=(
            "Today is {current_date}. Use the mandatory live-research packet below as the factual baseline.\n"
            "LIVE RESEARCH:\n{research}\n\n"
            "1. Prioritize the latest verified trends, key players, and noteworthy news on {topic}.\n"
            "2. Identify the target audience, their science/software baseline, interests, and pain points.\n"
            "3. Develop a detailed, connected outline including an introduction, key points, practical example, "
            "limitations, and a clear call to action.\n"

            "4. Build an evidence ledger that maps every proposed factual claim, statistic, clinical or "
            "scientific statement, current event, and attributed point of view to at least one source.\n"
            "5. For each source record its title, publisher/author, publication date when available, and direct URL. "
            "Prefer primary sources (original studies, official datasets, regulators, company filings, and direct "
            "statements); use reputable journalism for context or when no primary source is available.\n"
            "6. Include SEO keywords. Treat older model knowledge as stale whenever it conflicts with dated live "
            "research. Omit claims that cannot be supported by a source in the research packet.\n\n"
            f"{PLANNING_RULES}"

        ),
        expected_output=(
            "A focused content plan with reader intent, keyword brief, connected outline, evidence ledger, scope "
            "classification, researcher workflow, and internal-link/content-cluster opportunities."
        ),
        agent=planner,

    )

    write_task = Task(
        description=(
            "Today is {current_date}. Use the content plan and its live sources to craft a compelling blog post on {topic}.\n"
            "1. Follow the planned reader journey and incorporate SEO keywords naturally.\n"
            "2. Use the WordPress article contract below; do not expose the internal plan or classification labels.\n"
            "6. Cite every externally verifiable factual claim immediately after the sentence or paragraph using "
            "Markdown links, for example ([WHO](https://example.org/report)). This includes numbers, dates, "
            "comparisons, clinical/scientific findings, quotations, news, and claims about people or organizations.\n"
            "7. Clearly label analysis and opinions with phrasing such as 'In my view' or 'This suggests'. Support "
            "each point of view with links to the evidence, reporting, expert commentary, or data it interprets; do "
            "not present an opinion as settled fact.\n"
            "8. End with a '## References' section containing one bullet per cited source: source title, publisher "
            "or author, publication date when available, and a clickable direct URL. Every inline citation must "
            "appear in References, and every References entry must be cited in the article. Never invent a citation, "
            "title, date, author, or URL. Omit unsupported claims.\n"
            "9. Preserve dates and source links. Do not replace current facts with older model knowledge.\n\n"
            f"{WRITING_RULES}"
        ),
        expected_output=(
            "A publication-ready, reader-friendly WordPress Markdown article with claim-level inline citations, "
            "a complete References section, and a compact final SEO Details block."
        ),
        agent=writer,
    )

    edit_task = Task(
        description=(
            "Today is {current_date}. Proofread the given blog post for grammatical errors and alignment "
            "with the brand's voice. Perform a final citation audit sentence by sentence. Every factual claim, "
            "statistic, clinical/scientific statement, quotation, news item, and attributed or author point of view "
            "must have a nearby Markdown citation to a source that actually supports it. Clearly distinguish facts "
            "from analysis/opinion. Remove or qualify anything unsupported. Preserve verified dates and direct source "
            "URLs from the live research; never fabricate or guess bibliographic details. Ensure the final '## "
            "References' list is complete, deduplicated, and consistent with the inline citations. Do not introduce "
            "unsupported facts or revert current facts to older model knowledge.\n\n"
            f"{EDITORIAL_QUALITY_CHECK}"
        ),
        expected_output=(
            "A well-written blog post in markdown format (no leading word 'markdown'), ready for publication, "
            "with readable sections, evidence-backed viewpoints, clickable inline citations, a complete References "
            "section, and the final SEO Details block."
        ),
        agent=editor,
    )

    return Crew(
        agents=[planner, writer, editor],
        tasks=[plan_task, write_task, edit_task],
        verbose=settings["crew_verbose"],
        task_callback=show_task_completion,
    )


# Store crew in app state at startup
@app.on_event("startup")
def startup() -> None:
    app.state.search_tool = AutoSearchTool(
        provider=settings["search_provider"],
        gemini_model=settings["search_model"],
    )


@app.post("/generate-blog/")
async def generate_blog(request: TopicRequest) -> Dict[str, Any]:
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="'topic' must be provided")

    try:
        current_date = date.today().isoformat()
        show_progress(f"Researching current information for: {request.topic.strip()}")
        research_query = (
            f"As of {current_date}, research the latest verified facts and developments about: "
            f"{request.topic.strip()}. Prioritize primary and reputable recent sources. Include exact dates, "
            "current status, clinical or scientific studies, relevant datasets, contrasting expert viewpoints, "
            "and related news. For every fact or viewpoint, identify the supporting source title, publisher/author, "
            "publication date when available, and direct URL. Explicitly correct common outdated claims."
        )
        research = await asyncio.to_thread(
            app.state.search_tool._run,
            research_query,
        )
        if not research.strip():
            raise RuntimeError("Live research returned no results; refusing to generate a potentially stale report")
        show_progress("Live research complete; starting the agent workflow")

        # Search providers can return very large result payloads. Keeping the
        # packet bounded prevents an oversized prompt from producing an empty
        # LLM response while retaining ample room for current facts and URLs.
        research = research[:MAX_RESEARCH_CHARS]

        inputs = {
            "topic": request.topic.strip(),
            "current_date": current_date,
            "research": research,
        }
        result = None
        for attempt in range(LLM_EMPTY_RESPONSE_RETRIES + 1):
            # Crew and agent instances contain mutable execution state. A new
            # crew per attempt prevents state leaking across requests/retries.
            crew = build_crew()
            try:
                show_progress(
                    "Running planner, writer, and editor"
                    + (f" (retry {attempt})" if attempt else "")
                )
                # CrewAI and some of its tools use synchronous internals.
                result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
                blog_text = getattr(result, "raw", None) or str(result)
                references_valid, validation_error = validate_article_references(blog_text)
                if not references_valid:
                    if attempt >= LLM_EMPTY_RESPONSE_RETRIES:
                        raise RuntimeError(
                            "Generated article failed the citation audit: " + validation_error
                        )
                    logger.warning(
                        "Generated article failed the citation audit (%s); retrying with a fresh crew",
                        validation_error,
                    )
                    show_progress("Citation audit failed; regenerating the article with verified references")
                    result = None
                    continue
                break
            except ValueError as exc:
                is_empty_response = "Invalid response from LLM call - None or empty" in str(exc)
                if not is_empty_response or attempt >= LLM_EMPTY_RESPONSE_RETRIES:
                    raise
                delay_seconds = 2 ** attempt
                logger.warning(
                    "Gemini returned an empty response; retrying with a fresh crew in %s second(s) (%s/%s)",
                    delay_seconds,
                    attempt + 1,
                    LLM_EMPTY_RESPONSE_RETRIES,
                )
                show_progress(f"Gemini returned an empty response; retrying in {delay_seconds} second(s)")
                await asyncio.sleep(delay_seconds)

        if result is None:
            raise RuntimeError("Blog generation completed without a result")
        blog_text = getattr(result, "raw", None) or str(result)
        show_progress("Blog generation complete")
        return {"topic": request.topic, "blog": {"raw": blog_text}}
    except Exception as exc:
        logger.exception("Blog generation failed for topic %r", request.topic)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate-image/")
async def generate_image(request: TopicRequest) -> Dict[str, str]:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="'topic' must be provided")

    try:
        image_data = await asyncio.to_thread(generate_topic_image, topic)
        return {"imageUrl": f"data:{image_data}"}
    except Exception as exc:
        logger.exception("Image generation failed for topic %r", topic)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/download-word/")
async def download_word(request: DocumentRequest) -> StreamingResponse:
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Article content must be provided")

    try:
        document = await asyncio.to_thread(build_article_docx, request)
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", request.topic).strip("-")
        filename = f"{safe_stem or 'generated-article'}.docx"
        encoded_filename = quote(filename)
        return StreamingResponse(
            document,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
                )
            },
        )
    except Exception as exc:
        logger.exception("Word document creation failed for topic %r", request.topic)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
