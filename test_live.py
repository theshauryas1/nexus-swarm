import urllib.request, json, sys, time

BASE = "https://nexusswarm-backend-537381825142.us-central1.run.app"

sys.stdout.reconfigure(encoding="utf-8")

# ── 1. Submit the task ────────────────────────────────────────────────
payload = json.dumps({
    "title": "E-commerce REST API with authentication",
    "description": (
        "Build a secure REST API for an e-commerce platform. "
        "Include user auth with JWT, product catalog endpoints, "
        "shopping cart, order management, and payment integration with Stripe. "
        "Use FastAPI, PostgreSQL, and Redis for caching."
    )
}).encode("utf-8")

req = urllib.request.Request(
    f"{BASE}/submit-task",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

print("=" * 60)
print("  NexusSwarm Live Test — E-commerce API")
print("=" * 60)
print()
print("Submitting task...")

with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read())

task_id = result["task_id"]
print(f"  task_id : {task_id}")
print(f"  status  : {result['status']}")
print(f"  message : {result['message']}")
print()
print(f"  Tracking: {BASE}/task/{task_id}")
print()

# ── 2. Poll status every 8 seconds for up to 3 minutes ───────────────
print("Polling pipeline status (updates every 8s, max 3 min)...")
print("-" * 60)

start = time.time()
last_pipelines = {}

for _ in range(23):  # 23 * 8s = ~3 min
    time.sleep(8)
    
    try:
        status_req = urllib.request.Request(f"{BASE}/task/{task_id}")
        with urllib.request.urlopen(status_req, timeout=10) as sresp:
            data = json.loads(sresp.read())
    except Exception as e:
        print(f"  Poll error: {e}")
        continue

    overall = data.get("status", "?")
    pipelines = data.get("pipelines", [])

    changed = False
    for p in pipelines:
        name = p["name"]
        pstatus = p["status"]
        progress = p["progress"]
        key = f"{name}:{pstatus}:{progress}"
        if last_pipelines.get(name) != key:
            changed = True
            last_pipelines[name] = key
            bar = "#" * (progress // 5) + "-" * (20 - progress // 5)
            print(f"  [{bar}] {progress:3d}%  {name:<12} {pstatus}")

    if changed:
        print(f"  Overall: {overall}  (elapsed: {int(time.time()-start)}s)")
        print()

    if overall in ("complete", "failed", "blocked"):
        print("=" * 60)
        print(f"  FINAL STATUS: {overall.upper()}")
        outputs = data.get("outputs", {})
        if outputs:
            print(f"  Outputs generated: {list(outputs.keys())}")
            for key, val in list(outputs.items())[:3]:
                preview = str(val)[:200].replace("\n", " ")
                print(f"\n  [{key}]")
                print(f"  {preview}...")
        print("=" * 60)
        break
else:
    print("Polling timed out — pipeline still running. Check manually:")
    print(f"  GET {BASE}/task/{task_id}")
