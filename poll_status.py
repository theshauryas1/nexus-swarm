import urllib.request, json, sys, time
sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://nexusswarm-backend-537381825142.us-central1.run.app"
TASK_ID = "f60ece87-cd37-4ee7-9bcc-8b26311a43cc"

print("=" * 62)
print("  NexusSwarm Live Pipeline — E-commerce REST API")
print("=" * 62)

last_state = {}
start = time.time()

for i in range(20):
    time.sleep(20)

    req = urllib.request.Request(f"{BASE}/task/{TASK_ID}")
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read())

    overall = data.get("status", "?")
    pipelines = data.get("pipelines", [])
    outputs = data.get("outputs", {})

    elapsed = int(time.time() - start)
    print(f"\n[t+{elapsed}s] Overall: {overall}  |  Outputs: {len(outputs)}")

    for p in pipelines:
        pname   = p["name"]
        pstatus = p["status"]
        prog    = p["progress"]
        key     = f"{pstatus}:{prog}"
        changed = last_state.get(pname) != key
        last_state[pname] = key
        bar = "#" * (prog // 5) + "-" * (20 - prog // 5)
        marker = " <-- updated" if changed else ""
        print(f"  [{bar}] {prog:3d}%  {pname:<12} {pstatus}{marker}")

    if overall in ("complete", "failed", "blocked"):
        print()
        print("=" * 62)
        print(f"  FINAL STATUS: {overall.upper()}")
        print(f"  Total outputs: {len(outputs)}")
        print()
        for k, v in outputs.items():
            preview = str(v)[:400].replace("\n", " ")
            print(f"--- {k} ---")
            print(preview[:400])
            print()
        print("=" * 62)
        break
else:
    print("\nMax polls reached. Still running — check manually:")
    print(f"  GET {BASE}/task/{TASK_ID}")
