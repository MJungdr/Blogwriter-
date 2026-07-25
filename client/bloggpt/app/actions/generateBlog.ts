"use server"

const BACKEND_URL = "http://127.0.0.1:8002/generate-blog/";
const EARLY_RESET_RETRY_WINDOW_MS = 10_000;

interface BlogResponse {
    topic: string;
    blog: {
        raw: string;
    };
}

const isConnectionReset = (error: unknown): boolean => {
    if (!(error instanceof TypeError) || error.message !== "fetch failed") {
        return false;
    }

    const cause = (error as TypeError & { cause?: { code?: string } }).cause;
    return cause?.code === "ECONNRESET" || cause?.code === "ECONNREFUSED";
};

export const generateBlog = async (topic: string): Promise<BlogResponse> => {
    for (let attempt = 0; attempt < 2; attempt += 1) {
        const startedAt = Date.now();
        try {
            const response = await fetch(BACKEND_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ topic }),
                cache: "no-store",
            });

            if (!response.ok) {
                let message = `Backend request failed (${response.status})`;
                try {
                    const errorBody = await response.json();
                    if (typeof errorBody?.detail === "string") {
                        message = errorBody.detail;
                    }
                } catch {
                    // Keep the status-based message when the backend did not return JSON.
                }
                throw new Error(message);
            }
            return await response.json() as BlogResponse;
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
