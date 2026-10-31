import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 150_000 });

// Admin token lives only in this browser tab (sessionStorage), never in the bundle.
const TOKEN_KEY = "gatherly_admin_token";

export const adminToken = {
  get: () => {
    try {
      return sessionStorage.getItem(TOKEN_KEY) || "";
    } catch {
      return "";
    }
  },
  set: (token) => {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage blocked: token just won't persist */
    }
  },
  clear: () => {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

client.interceptors.request.use((config) => {
  const token = adminToken.get();
  if (token) config.headers["X-Admin-Token"] = token;
  return config;
});

// Surface the API's own message ("Too many plan requests. Try again in 12s.")
// instead of axios' generic "Request failed with status code 429".
client.interceptors.response.use(
  (r) => r,
  (error) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === "string") error.message = detail;
    return Promise.reject(error);
  }
);

const newIdempotencyKey = () =>
  (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`).toString();

export const api = {
  health: () => client.get("/health").then((r) => r.data),
  samplePrompts: () => client.get("/sample-prompts").then((r) => r.data),
  architecture: () => client.get("/architecture").then((r) => r.data),
  vendors: () => client.get("/vendors").then((r) => r.data),
  createPlan: (request) =>
    client
      .post("/plans", { request }, { headers: { "Idempotency-Key": newIdempotencyKey() } })
      .then((r) => r.data),
  decide: (planId, decision) =>
    client
      .post(`/plans/${planId}/decision`, { decision })
      .then((r) => r.data),
  listPlans: (params) => client.get("/plans", { params }).then((r) => r.data),
  getPlan: (planId) => client.get(`/plans/${planId}`).then((r) => r.data),
  deletePlan: (planId) => client.delete(`/plans/${planId}`).then((r) => r.data),
  exportUrl: (planId, format) => `${API}/plans/${planId}/export.${format}`,
};
