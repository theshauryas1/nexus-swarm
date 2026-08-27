import urllib.request
import json
import time

BASE = "https://nexusswarm-backend-669943047856.us-central1.run.app"

payload = json.dumps({
    "title": "Secure JWT Auth API with Rate Limiter",
    "description": "Build a lightweight FastAPI service with JWT auth, token expiration, and Redis rate limiting."
}).encode("utf-8")

req = urllib.request.Request(
    f"{BASE}/submit-task",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=15) as resp:
    res = json.loads(resp.read())

task_id = res["task_id"]
print(f"Submitted Task ID: {task_id}", flush=True)

for i in range(15):
    time.sleep(5)
    s_req = urllib.request.Request(f"{BASE}/task/{task_id}")
    with urllib.request.urlopen(s_req, timeout=10) as sresp:
        data = json.loads(sresp.read())
    status = data.get("status")
    pipelines = data.get("pipelines", [])
    parts = [f"{p['name']}:{p['status']}({p['progress']}%)" for p in pipelines]
    print(f"[{(i+1)*5}s] Status: {status} | Pipelines: {', '.join(parts)}", flush=True)
    if status in ("complete", "failed", "blocked"):
        outputs = data.get("outputs", {})
        print(f"PIPELINE COMPLETE! Total outputs: {len(outputs)}", flush=True)
        for k in list(outputs.keys())[:4]:
            print(f"  - Output key: {k}")
        break
