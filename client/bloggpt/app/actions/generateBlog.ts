"use server"

import { request } from "node:http";

const BACKEND_URL = "http://127.0.0.1:8002/generate-blog/";
const EARLY_RESET_RETRY_WINDOW_MS = 10_000;
const GENERATION_TIMEOUT_MS = 20 * 60 * 1_000;

export type ArticleType =
    | "auto"
    | "research"
    | "ai_tool"
    | "global_life"
    | "hybrid";

export type OptionalContentState = "auto" | "include" | "exclude";

export interface OptionalContentOptions {
    mimiExample: OptionalContentState;
    workflow: OptionalContentState;
    myView: OptionalContentState;
}

interface BlogResponse {
    topic: string;
    requested_article_type: ArticleType;
    article_type: Exclude<ArticleType, "auto">;
    blog: {
        raw: string;
    };
}

export type GenerateBlogResult =
    | { ok: true; data: BlogResponse }
    | { ok: false; error: string };

interface BackendHttpResponse {
    status: number;
    body: string;
}

const postToBackend = (
    topic: string,
    articleType: ArticleType,
    options: OptionalContentOptions,
): Promise<BackendHttpResponse> => {
    const payload = JSON.stringify({
        topic,
        article_type: articleType,
        mimi_example: options.mimiExample,
        workflow: options.workflow,
        my_view: options.myView,
    });

    return new Promise((resolve, reject) => {
        const backendRequest = request(
            BACKEND_URL,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(payload),
                },
            },
            (backendResponse) => {
                const chunks: Buffer[] = [];
                backendResponse.on("data", (chunk: Buffer) => chunks.push(chunk));
                backendResponse.on("end", () => {
                    resolve({
                        status: backendResponse.statusCode ?? 500,
                        body: Buffer.concat(chunks).toString("utf8"),
                    });
                });
                backendResponse.on("error", reject);
                backendResponse.on("aborted", () => {
                    reject(new Error("The backend closed the generation connection before responding"));
                });
            },
        );

        backendRequest.setTimeout(GENERATION_TIMEOUT_MS, () => {
            backendRequest.destroy(
                new Error("Article generation exceeded the 20-minute timeout"),
            );
        });
        backendRequest.on("error", reject);
        backendRequest.write(payload);
        backendRequest.end();
    });
};

const isConnectionReset = (error: unknown): boolean => {
    const code = (error as NodeJS.ErrnoException)?.code;
    return code === "ECONNRESET" || code === "ECONNREFUSED";
};

export const generateBlog = async (
    topic: string,
    articleType: ArticleType,
    options: OptionalContentOptions,
): Promise<GenerateBlogResult> => {
    for (let attempt = 0; attempt < 2; attempt += 1) {
        const startedAt = Date.now();
        try {
            const response = await postToBackend(topic, articleType, options);

            if (response.status < 200 || response.status >= 300) {
                let message = `Backend request failed (${response.status})`;
                try {
                    const errorBody = JSON.parse(response.body);
                    if (typeof errorBody?.detail === "string") {
                        message = errorBody.detail;
                    }
                } catch {
                    // Keep the status-based message when the backend did not return JSON.
                }
                return { ok: false, error: message };
            }
            return { ok: true, data: JSON.parse(response.body) as BlogResponse };
        } catch (error) {
            const failedEarly = Date.now() - startedAt < EARLY_RESET_RETRY_WINDOW_MS;
            if (attempt === 0 && failedEarly && isConnectionReset(error)) {
                console.warn("Backend connection restarted; retrying once...");
                await new Promise((resolve) => setTimeout(resolve, 750));
                continue;
            }
            console.error("Blog generation request failed", error);
            return {
                ok: false,
                error:
                    error instanceof Error
                        ? error.message
                        : "The blog generation request failed unexpectedly",
            };
        }
    }

    return {
        ok: false,
        error: "The backend could not be reached after retrying once",
    };
};
