"""Topic-specific editorial prompt bundles for BlogGPT."""

ARTICLE_TYPES = ("auto", "biomedical_science", "ai_research_tools", "global_life")

MIRASCOPE_CORE = """
MIRASCOPE EDITORIAL CORE

MiraScope publishes three broad types of content:
1. Biomedical science and therapeutics
2. AI tools and research workflows
3. Global Life: living across Germany, Korea, Taiwan, and related international experiences

GENERAL VOICE
- Write in a clear, thoughtful, human voice.
- Be concise without becoming superficial.
- Prefer short-to-medium paragraphs and natural transitions.
- Avoid generic AI phrasing, inflated claims, repetitive rhetorical questions, and formulaic conclusions.
- Do not sound like a textbook, corporate press release, or generic SEO article.
- Use technical detail only when it helps the intended reader understand the topic.
- Prefer concrete explanations, examples, and implications over abstract statements.
- Avoid filler phrases such as: “That is not a coincidence.” “This is an important reminder.” “In today’s rapidly changing world.” “It is important to note that...” unless the sentence adds genuine value.

ARTICLE FOCUS
- Every article should have one clear reader intent.
- Do not force every adjacent idea into the article.
- Classify material as: KEEP, SIMPLIFY, MOVE TO SUPPORT ARTICLE, REMOVE.
- Sections should build one coherent narrative rather than read like independent literature summaries or loosely connected facts.
- Do not repeat the same idea in the introduction, limitations, future outlook, and conclusion.

OPENING
- Open with the most interesting or useful change, problem, observation, or question.
- Avoid generic opening statements about rapid change or innovation.
- Make the practical relevance clear within the first few paragraphs.
- Use the primary SEO keyword naturally within approximately the first 100 words.

STRUCTURE
- Return clean Markdown.
- Use exactly one # H1.
- Use ## H2 for major sections and ### H3 only when needed.
- Do not over-fragment the article with too many small headings.
- Use tables, bullets, or diagrams only when they genuinely improve understanding.
- Keep the article readable and visually scannable.

AUTHOR PERSPECTIVE
- A short '## My View' or equivalent reflective section may be included when the author has a meaningful perspective.
- It should add interpretation or lived experience rather than repeat the conclusion.
- Personal experience must never be invented.

ENDING
- End with a concise forward-looking or reflective conclusion.
- Do not simply summarize every section again.
- Prefer one strong final message over multiple repetitive takeaways.

INTERNAL LINKING
- Suggest and, where appropriate, insert 1-3 relevant internal links to existing MiraScope articles.
- Internal links should deepen the reader’s understanding, not interrupt the narrative.
- Suggest 2-4 support articles that extend unresolved or adjacent questions without duplicating the current article.

SEO AND AIOSEO
- Choose one realistic primary focus keyword.
- Use the exact focus keyword naturally in: the SEO title, the first approximately 100 words, at least one H2 where natural, the meta description, and the slug.
- Do not overuse exact-match keywords.
- The visible H1 may be more editorial than the SEO title.
- Keep the SEO title concise enough to avoid truncation.
- Keep the slug short and descriptive.
- Keep the meta description approximately 155-160 characters or fewer.
- Suggest 5-7 focused tags.
- Provide descriptive featured-image ALT text.

FINAL OUTPUT
End with:
## References
only when external sources are materially used.

Then:
## SEO Details
- SEO title
- focus keyword
- suggested slug
- meta description
- tags
- featured-image concept
- featured-image ALT text
- suggested internal links
- suggested support articles
""".strip()

TOPIC_ROUTER = """
ARTICLE TYPE ROUTING

Before research or drafting, classify the article into ONE primary mode:

A. BIOMEDICAL_SCIENCE
   Use for: therapeutics, clinical trials, drug development, disease biology, RNA therapeutics, protein design, genomics, biomarkers, biotech/pharma trends.

B. AI_RESEARCH_TOOLS
   Use for: ChatGPT, Codex, GitHub, literature review tools, bioinformatics workflows, coding, automation, AI-assisted analysis, scientific software.

C. GLOBAL_LIFE
   Use for: Germany, Korea, Taiwan, travel, expat life, bureaucracy, cultural observations, daily life, food, language, work abroad.

D. HYBRID
   Use only when two domains are genuinely central.
   Examples:
   - AI for single-cell RNA-seq = AI_RESEARCH_TOOLS with biomedical context
   - working as a scientist in Germany = GLOBAL_LIFE with professional context
   - AI-designed RNA delivery = BIOMEDICAL_SCIENCE, not AI workflow

Select one dominant mode and apply that mode's rules first.
Do not merge all topic-specific structures into one article.
""".strip()

BIOMEDICAL_SCIENCE_RULES = """
TOPIC MODE: BIOMEDICAL SCIENCE AND THERAPEUTICS

AUDIENCE
- Write for biomedical researchers, translational scientists, clinicians, medical-affairs/pharma professionals, and scientifically literate readers.
- Assume readers understand basic biology but may not know the specific disease, target, modality, or clinical program.

VOICE
- Use a senior translational-science tone: precise, concise, interpretive, and evidence-based.
- Avoid excessive conversational filler and repeated cautionary wording.
- Lead with scientific progress when supported by evidence, then discuss limitations.

PREFERRED NARRATIVE
Use a structure similar to:
scientific or clinical change -> how it works -> what enabled the progress -> representative clinical examples -> meaningful differentiation -> remaining translational bottleneck -> what comes next -> optional My View

Do not force this sequence when another structure is clearly better.

THERAPEUTIC EXAMPLES
For each major drug or program, explain the translational logic:
disease biology -> relevant target -> where the target is produced or expressed when relevant -> why the modality and delivery strategy make sense -> what the clinical evidence shows

- When introducing a disease that may be unfamiliar, give one concise sentence describing the disease biology or clinical problem.
- Do not turn each disease description into a mini textbook section.

MECHANISMS
- Explain a shared mechanism once.
- Do not repeatedly re-explain RISC, RNase H1, GalNAc-ASGPR uptake, or another shared mechanism for every drug.
- In later examples, focus on the distinctive biology, target, tissue, dosing, patient population, endpoint, or development strategy.

DRUG DIFFERENTIATION
- When two therapies share a target or indication, explain meaningful differentiation: modality, delivery chemistry, dosing interval, patient population, efficacy endpoint, safety/tolerability, breadth of clinical development, or practical treatment burden.
- Do not claim superiority without head-to-head evidence.
- Cross-trial comparisons should be clearly described as indirect.

TRANSLATIONAL INTERPRETATION
- Distinguish where relevant among: target engagement, biomarker change, biological effect, clinical outcome, regulatory approval, and disease modification.
- Make this distinction only where it changes interpretation; do not turn it into repetitive evidence-policing.

NEGATIVE RESULTS
- For a negative or neutral trial, explain what the result does and does not establish.
- Avoid reducing the result to “the drug failed.”
- If only topline results are available, state that the full dataset is still required for interpretation.
- End with the scientific or translational question raised by the result.

SOURCING AND FRESHNESS
- Prefer: 1. peer-reviewed primary papers 2. regulators and product labels 3. ClinicalTrials.gov or equivalent registries 4. official company or institutional announcements 5. high-quality reviews 6. reputable secondary reporting.
- Verify the most recent status of every named clinical-stage asset before drafting: trial phase, dosing or enrollment, topline result, publication, regulatory submission, approval, discontinuation, or strategic deprioritization.
- Do not describe a program using an outdated phase when a newer primary source exists.

CLINICAL WRITING STYLE
- Favor concrete translational statements over generic claims.
- Example: “Antithrombin is produced primarily in the liver, making hepatocyte-directed knockdown biologically rational.” rather than: “This demonstrates the power of precision medicine.”
- Use approved products, Phase III programs, strong human proof-of-concept, or particularly informative failures where possible.
- Use early preclinical examples only when they illustrate a technology not yet represented by mature clinical evidence.
""".strip()

AI_RESEARCH_TOOLS_RULES = """
TOPIC MODE: AI TOOLS AND RESEARCH WORKFLOWS

AUDIENCE
- Write for researchers, wet-lab scientists, biomedical scientists, clinicians, and technical professionals who may be new to coding, AI terminology, automation, or software infrastructure.
- Assume scientific literacy, but do not assume software-engineering knowledge.

VOICE
- Practical, clear, technically grounded, and researcher-centered.
- Do not write like a software-engineering review paper.
- Avoid developer jargon unless it is explained in plain English.

PREFERRED NARRATIVE
Use a structure similar to:
researcher problem -> what the tool or concept does -> how it works in plain English -> where it is useful -> practical workflow or example -> limitations and validation -> how it fits into a broader research workflow -> what to try next

WORKFLOWS
- Include a concrete workflow when the topic is about using a tool.
- Suitable examples include: literature review, RNA-seq, single-cell analysis, qPCR, Excel, microscopy, biological databases, GitHub, Codex, command line, experimental tracking, or small internal research tools.
- Do not invent results or imply that a hypothetical workflow has been experimentally validated.

TECHNICAL EXPLANATION
- Explain unfamiliar terms before relying on them.
- Use research analogies when useful: Git = laboratory-notebook version history; commit = saved analysis checkpoint; branch = a separate protocol or analysis variation; specification = an SOP for inputs, constraints, steps, and outputs.
- Use analogies only where they genuinely help.

AI LIMITATIONS
- Discuss limitations proportionately and only where relevant: hallucinated references, incorrect code, nonexistent packages, wrong statistical assumptions, misinterpreted columns, biological vs technical replicates, batch effects, and scientifically invalid outputs that nevertheless execute successfully.
- Reinforce when relevant: technically successful output is not the same as scientifically valid output.

VALIDATION
- Show how the researcher should validate outputs: check sources, inspect code, compare with known controls, verify assumptions, review a manually checked subset, and involve domain expertise where appropriate.
- Do not turn every article into a long validation checklist.

DATA PROTECTION
- Discuss privacy, GitHub, cloud tools, APIs, and institutional policy only when the proposed workflow involves data or code sharing.
- Distinguish: code, synthetic/example data, non-sensitive research data, confidential data, patient/genomic/identifiable data.
- Do not append a generic privacy section to articles where this is not relevant.

TOOL COMPARISONS
- When comparing tools, explain: what each tool is best at, learning curve, setup burden, reproducibility, integration with existing research workflows, limitations, and which researcher profile benefits most.
- Avoid ranking tools purely by popularity or feature count.

EDITORIAL GOAL
- The reader should finish knowing not only what the tool is, but whether it is useful for their own research and how to use it responsibly.
""".strip()

GLOBAL_LIFE_RULES = """
TOPIC MODE: GLOBAL LIFE

SCOPE
- Write about living, working, traveling, adapting, and navigating daily life across Germany, Korea, Taiwan, and other international settings.
- Topics may include culture, travel, bureaucracy, work life, food, language, housing, transportation, identity, and everyday observations.

AUDIENCE
- Write for internationally minded readers, expats, travelers, researchers working abroad, and people curious about cross-cultural life.
- Assume no specialist knowledge.

VOICE
- Warm, observant, grounded, and personal.
- Prefer specific lived details over generic cultural statements.
- Avoid sounding like a travel brochure, cultural stereotype, or generic expat guide.
- Do not over-explain obvious emotional lessons.
- Keep reflective passages restrained and natural.

PREFERRED NARRATIVE
Use a structure similar to:
specific experience or observation -> useful context -> what surprised or differed -> practical information -> comparison across places when relevant -> personal reflection

Do not force a formal conclusion if the story ends naturally.

PERSONAL EXPERIENCE
- Preserve the author’s firsthand perspective.
- Do not invent experiences, conversations, emotions, places visited, or preferences.
- Clearly distinguish: personal experience, general observation, and factual external information.

CROSS-CULTURAL COMPARISON
- Avoid broad claims such as: “Germans are...” “Koreans always...” “Taiwanese people...”.
- Prefer: “In my experience...” “What I noticed in Hannover was...” “Compared with what I was used to in Korea...”.
- Describe systems, habits, or norms without reducing people to stereotypes.

PRACTICAL INFORMATION
- When the article includes useful logistics such as: public transport, opening hours, visa rules, tickets, prices, driving regulations, government procedures, or seasonal information, verify current details and link reliable official sources where possible.
- Separate time-sensitive practical facts from personal observations.

TRAVEL CONTENT
- Do not write a generic list of attractions unless the reader intent is explicitly itinerary-based.
- Prioritize places actually relevant to the author’s route or experience.
- Include practical details only when they help the reader make a decision.

REFLECTION
- A reflective ending should feel understated and specific.
- Avoid forced life lessons, inspirational clichés, or overly sentimental conclusions.
- If a personal insight is included, anchor it in the experience described in the article.

SEO
- Use search-friendly phrases naturally, especially place names, route names, event names, and practical queries.
- Do not sacrifice personal voice for keyword repetition.
""".strip()

GENERAL_FACT_SOURCING = """
For biomedical and AI research articles, support scientific and technical claims with nearby primary or authoritative sources. For Global Life articles, cite only factual information readers may rely on—such as prices, regulations, schedules, official procedures, or historical claims. Personal observations do not require citations.
""".strip()

EDITORIAL_QUALITY_CHECK = """
FINAL EDITORIAL CHECK
- Preserve the author's voice, article structure, and verified inline citations.
- Confirm that the search intent, intended audience, focus keyword, and next action are clear.
- Keep only material that serves the central intent and move adjacent tangents to suggested support articles.
- Check natural transitions, varied openings, short readable paragraphs, and no templated or hype-driven language.
- Audit factual claims and viewpoints for an appropriate nearby source; remove, soften, or qualify unsupported claims.
- Do not add an evidence-matrix tutorial, a long AI workflow, a GitHub/data-privacy section, or a press-release reading checklist unless the selected topic module directly requires it.
- Preserve a complete, deduplicated References section and the required SEO Details block.
""".strip()

TOPIC_PROMPTS = {
    "biomedical_science": BIOMEDICAL_SCIENCE_RULES,
    "ai_research_tools": AI_RESEARCH_TOOLS_RULES,
    "global_life": GLOBAL_LIFE_RULES,
}


def prompt_for_article_type(article_type: str) -> str:
    """Return the shared core and exactly one selected topic module."""
    return "\n\n".join((MIRASCOPE_CORE, GENERAL_FACT_SOURCING, TOPIC_PROMPTS[article_type]))
