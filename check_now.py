import urllib.request, json, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://nexusswarm-backend-537381825142.us-central1.run.app"
TASK_ID = "f60ece87-cd37-4ee7-9bcc-8b26311a43cc"

req = urllib.request.Request(f"{BASE}/task/{TASK_ID}")
with urllib.request.urlopen(req, timeout=12) as resp:
    data = json.loads(resp.read())

overall = data.get("status")
print("OVERALL STATUS:", overall)
print()

for p in data.get("pipelines", []):
    prog = p["progress"]
    bar = "#" * (prog // 5) + "-" * (20 - prog // 5)
    print(f"  [{bar}] {prog:3d}%  {p['name']:<12} {p['status']}")

outputs = data.get("outputs", {})
print()
print(f"Total outputs: {len(outputs)}")
print("Keys:", list(outputs.keys()))

if overall in ("complete", "failed", "blocked"):
    print()
    print("=== PIPELINE COMPLETE — OUTPUT PREVIEWS ===")
    for k, v in outputs.items():
        preview = str(v)[:350].replace("\n", " ")
        print(f"\n[{k}]")
        print(preview)
