#!/usr/bin/env python3
import os
import sys
import io
import asyncio
import logging

# Ensure UTF-8 terminal encoding on Windows to prevent UnicodeEncodeError for emojis
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup path and env variables
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_PROVIDER"] = "nvidia"  # Direct execution via NVIDIA NIM cloud provider

# Set logging to INFO to print progress to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from routes import run_swarm_pipeline, active_tasks

async def main():
    task_id = "nim-cloud-test-task-1"
    title = "Interactive Travel Blog and Storytelling Platform"
    description = (
        "Build a modern, highly interactive travel blog and storytelling platform for a solo explorer. "
        "The application needs to serve a beautiful responsive React frontend containing a travel story grid, "
        "an interactive map placeholder component showing pinned locations, and an elegant newsletter subscription contact form. "
        "The backend must serve travel post content via a secure FastAPI endpoint, implement input validation for subscriptions, "
        "and enforce rate limiting (60 requests/min). Exclude active deployment executions but generate a production "
        "Dockerfile and a GitHub Actions deploy.yaml targeting Google Cloud Run. Keep all generated files safely in the workspace."
    )

    print("\n" + "="*80)
    print("STARTING NEXUSSWARM PIPELINE RUN ON CLOUD (NVIDIA NIM)")
    print(f"Task: {title}")
    print(f"Description: {description}")
    print("="*80 + "\n")

    # Pre-populate active_tasks
    active_tasks[task_id] = {
        "task_id":   task_id,
        "status":    "running",
        "title":     title,
        "created_at": "2026-05-31T11:00:00Z",
        "outputs":   {},
        "pipelines": [
            {"name": "planning",    "status": "idle", "progress": 0},
            {"name": "engineering", "status": "idle", "progress": 0},
            {"name": "qa",          "status": "idle", "progress": 0},
            {"name": "security",    "status": "idle", "progress": 0},
            {"name": "devops",      "status": "idle", "progress": 0},
            {"name": "reliability", "status": "idle", "progress": 0},
        ],
    }

    try:
        # Run swarm pipeline
        await run_swarm_pipeline(task_id, title, description)
    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

    task_state = active_tasks.get(task_id, {})
    outputs = task_state.get("outputs", {})

    print("\n" + "="*80)
    print("NEXUSSWARM PIPELINE COMPLETED")
    print(f"Final Task Status: {task_state.get('status')}")
    print("="*80 + "\n")

    # Generate Markdown Report of all agent responses
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "workspace",
        "nim_test_report.md"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    report_content = f"""# NVIDIA NIM Cloud Swarm Pipeline Execution Report

- **Task Title:** {title}
- **Description:** {description}
- **Final Status:** {task_state.get('status')}

---

## Agent Output Artifacts

"""
    for key, val in sorted(outputs.items()):
        report_content += f"### Agent / Artifact: `{key}`\n\n```\n{val}\n```\n\n---\n\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Executed successfully. Comprehensive report recorded at:\n{report_path}\n")

if __name__ == "__main__":
    asyncio.run(main())
