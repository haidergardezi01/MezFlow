import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

const PROD_BACKEND_URL = "https://mezflow.vercel.app/api/v1";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.startsWith("192.168.") ||
    window.location.hostname.startsWith("10.") ||
    window.location.hostname.startsWith("172."))
    ? "http://127.0.0.1:8000/api/v1"
    : PROD_BACKEND_URL);

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000, // 45 seconds to comfortably tolerate serverless cold starts
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Request interceptor: Inject dynamic baseURL, Bearer token, or Diner ID if present
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      // 1. Explicit environment variable if configured
      if (process.env.NEXT_PUBLIC_API_URL) {
        config.baseURL = process.env.NEXT_PUBLIC_API_URL;
      } else if (
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname.startsWith("192.168.") ||
        window.location.hostname.startsWith("10.") ||
        window.location.hostname.startsWith("172.")
      ) {
        // 2. Localhost and Wi-Fi LAN IP testing
        const host =
          window.location.hostname === "localhost"
            ? "127.0.0.1"
            : window.location.hostname;
        config.baseURL = `http://${host}:8000/api/v1`;
      } else {
        // 3. Production Vercel or cloud deployment
        config.baseURL = PROD_BACKEND_URL;
      }

      let token = localStorage.getItem("mezflow_token");
      if (!token && (window as any).Clerk?.session) {
        try {
          const clerkToken = (window as any).Clerk.session.lastActiveToken?.jwt;
          if (clerkToken) token = clerkToken;
        } catch {
          // ignore
        }
      }
      if (token && config.headers && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      const dinerId = localStorage.getItem("mezflow_diner_id");
      if (dinerId && config.headers && !config.headers["X-Diner-ID"]) {
        config.headers["X-Diner-ID"] = dinerId;
      }
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor: Auto-retry on cold-start timeouts and uniform error formatting
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    // Auto-retry once on timeout or cold-start network drop
    if (
      originalRequest &&
      !originalRequest._retry &&
      (error.code === "ECONNABORTED" ||
        error.message?.toLowerCase().includes("timeout") ||
        !error.response)
    ) {
      originalRequest._retry = true;
      try {
        return await apiClient(originalRequest);
      } catch (retryError) {
        // Fall through to error extraction below
      }
    }

    // FastAPI validation errors (422) send detail as a list of {loc, msg}; show the messages, not "[object Object]"
    const detail: unknown = error.response?.data?.detail;
    const fieldMessages: Record<string, string> = {
      email: "Email address is not valid. Please check it (e.g. name@gmail.com).",
      username: "Please enter your email address.",
      password: "Password is too short. Use at least 8 characters.",
      new_password: "New password is too short.",
      code: "The code must be exactly 6 digits.",
      restaurant_name: "Restaurant name must be at least 2 characters.",
      manager_name: "Owner name must be at least 2 characters.",
    };
    const detailText = Array.isArray(detail)
      ? Array.from(
          new Set(
            detail.map((d: any) => {
              const field = Array.isArray(d?.loc) ? String(d.loc[d.loc.length - 1]) : "";
              return fieldMessages[field] || String(d?.msg || "").replace(/^Value error, /, "");
            })
          )
        )
          .filter(Boolean)
          .join(" ")
      : typeof detail === "string"
        ? detail
        : "";
    const message =
      detailText ||
      error.message ||
      "An unexpected network error occurred.";
    return Promise.reject(new Error(message));
  }
);

/**
 * Non-blocking background warmup call to wake up the serverless backend
 * and warm the database connection pool before user actions.
 */
export function warmupBackend(): void {
  if (typeof window === "undefined") return;
  apiClient.get("/health").catch(() => {});
}

export default apiClient;
