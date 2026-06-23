import axios from "axios";

export async function fetchRuns() {
  const response = await axios.get(`/api/runs`);
  return response.data;
}