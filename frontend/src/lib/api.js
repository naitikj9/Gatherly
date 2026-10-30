import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 90_000 });

export const api = {
  health: () => client.get("/health").then((r) => r.data),
  samplePrompts: () => client.get("/sample-prompts").then((r) => r.data),
  architecture: () => client.get("/architecture").then((r) => r.data),
  vendors: () => client.get("/vendors").then((r) => r.data),
  createPlan: (request) =>
    client.post("/plans", { request }).then((r) => r.data),
  decide: (planId, decision) =>
    client
      .post(`/plans/${planId}/decision`, { decision })
      .then((r) => r.data),
  listPlans: () => client.get("/plans").then((r) => r.data),
  getPlan: (planId) => client.get(`/plans/${planId}`).then((r) => r.data),
  deletePlan: (planId) => client.delete(`/plans/${planId}`).then((r) => r.data),
  exportUrl: (planId, format) => `${API}/plans/${planId}/export.${format}`,
};
