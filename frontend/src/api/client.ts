import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default apiClient;

/* ---------- Pipeline API ---------- */

export async function pipelineUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post("/pipeline/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export interface SimulateConfig {
  upload_id: string;
  scenario_name: string;
  scenario_type: string;
  target_page: string;
  variants: { name: string; description: string }[];
  twin_count?: number;
  primary_metric?: string;
  reaction_rules?: unknown[];
  analysis_tags?: string[];
  analysis_dimensions?: unknown[];
}

export async function pipelineSimulate(config: SimulateConfig) {
  const res = await apiClient.post("/pipeline/simulate", config);
  return res.data;
}

export async function musinsaOneClick() {
  const res = await apiClient.post("/sample-data/musinsa");
  return res.data;
}

export async function getSimulationReport(id: string) {
  const res = await apiClient.get(`/simulations/${id}/report`);
  return res.data;
}
