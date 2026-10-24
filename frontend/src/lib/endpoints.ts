// NEXT_PUBLIC_API_URL set (e.g. "/api/v1" on Vercel) → API and sockets on that origin.
// Unset → backend on this host's port 8000 (local dev and mobile Wi-Fi testing).
const devHost = () =>
  `${window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname}:8000`;

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || `http://${devHost()}/api/v1`;
}

export function wsBaseUrl(): string {
  const api = process.env.NEXT_PUBLIC_API_URL;
  if (!api) return `${window.location.protocol === "https:" ? "wss" : "ws"}://${devHost()}`;
  const url = new URL(api, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString().replace(/\/$/, "");
}
