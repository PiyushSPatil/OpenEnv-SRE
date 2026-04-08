const API_BASE = import.meta.env.VITE_API_URL;

export async function resetEnv(task_id) {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ task_id }),
  });
  return res.json();
}

export async function stepEnv(action) {
  const res = await fetch(`${API_BASE}/step`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(action),
  });
  return res.json();
}

export async function getState() {
  const res = await fetch(`${API_BASE}/state`);
  return res.json();
}