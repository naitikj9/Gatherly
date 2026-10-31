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

// POST /plans/stream: Server-Sent Events over fetch (EventSource can't POST).
// Calls onStep({node, message, ts}) as each agent works; resolves with the plan.
async function streamPlan(request, { onStart, onStep, signal } = {}) {
  const res = await fetch(`${API}/plans/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ request }),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue; // keep-alive comment
      const payload = JSON.parse(data);
      if (event === "start") onStart?.(payload);
      else if (event === "step") onStep?.(payload);
      else if (event === "done") return payload;
      else if (event === "error") throw new Error(payload.detail || "Planning failed");
    }
  }
  throw new Error("The connection closed before the plan was ready.");
}

export const api = {
  streamPlan,
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
  whatIf: (planId, params) => client.post(`/plans/${planId}/whatif`, params).then((r) => r.data),
  invite: (planId) => client.get(`/plans/${planId}/invite`).then((r) => r.data),
  rsvp: (planId, body) => client.post(`/plans/${planId}/rsvp`, body).then((r) => r.data),
  rsvps: (planId) => client.get(`/plans/${planId}/rsvps`).then((r) => r.data),
};
