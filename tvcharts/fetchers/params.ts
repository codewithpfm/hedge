import axios from "axios";

export async function fetchParams(runId: string) {
  const response = await axios.get(`/api/params?runId=${runId}`);
  return response.data;
}
