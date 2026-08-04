"use server"

import { request } from "node:http";

const BACKEND_URL = "http://127.0.0.1:8002/generate-blog/";
const EARLY_RESET_RETRY_WINDOW_MS = 10_000;
const GENERATION_TIMEOUT_MS = 20 * 60 * 1_000;

interface BlogResponse {
    topic: string;
    blog: {
        raw: string;
    };
}

interface BackendHttpResponse {
    status: number;
    body: string;
}

const postToBackend = (topic: string): Promise<BackendHttpResponse> => {
    const payload = JSON.stringify({ topic });

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

export const generateBlog = async (topic: string): Promise<BlogResponse> => {
    for (let attempt = 0; attempt < 2; attempt += 1) {
        const startedAt = Date.now();
        try {
            const response = await postToBackend(topic);

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
                throw new Error(message);
            }
            return JSON.parse(response.body) as BlogResponse;
        } catch (error) {
            const failedEarly = Date.now() - startedAt < EARLY_RESET_RETRY_WINDOW_MS;
            if (attempt === 0 && failedEarly && isConnectionReset(error)) {
                console.warn("Backend connection restarted; retrying once...");
                await new Promise((resolve) => setTimeout(resolve, 750));
                continue;
            }
            console.error(error);
            throw error;
        }
    }

    throw new Error("Backend request failed after retry");
};
