/**
 * Shared utility for resolving the backend API base URL.
 *
 * Server-side routes check API_BASE_URL first, then NEXT_PUBLIC_API_BASE_URL.
 * Client-side code relies on NEXT_PUBLIC_API_BASE_URL only (Next.js inlines
 * it at build time).
 *
 * In production (NODE_ENV === "production") the function throws at module init
 * if no URL is configured.  In development / test it falls back to the local
 * dev server so that running `npm run dev` works out of the box.
 */
export function getRequiredApiBaseUrl(): string {
  const raw = (
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL
  )?.replace(/\/+$/, "");

  if (!raw && process.env.NODE_ENV === "production") {
    throw new Error(
      "API_BASE_URL (or NEXT_PUBLIC_API_BASE_URL) is not set. " +
      "This environment variable is required in production. " +
      "Set it to the backend API base URL (e.g. https://api.example.com).",
    );
  }

  return raw || "http://localhost:8000/api/v1";
}
