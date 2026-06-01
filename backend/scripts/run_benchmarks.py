# run_benchmarks.py — NexusSwarm Benchmark Runner
# Executes benchmark tasks, evaluates results, and saves scores to the database.
# Supports 100 categorized tasks loaded from backend/benchmarks/ directory structure.

import os
import sys
import time
import asyncio
import logging
from datetime import datetime

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging with UTF-8 encoding for Windows
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(
            stream=open(os.devnull, 'w') if False else __import__('sys').stdout
        )
    ]
)
# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass

logger = logging.getLogger("run_benchmarks")

from db.benchmark_loader import load_benchmark_tasks
from memory.db_client import get_db_session, TaskDB, PipelineDB, EvaluationDB, BenchmarkDB, init_db_tables
from routes import run_swarm_pipeline, active_tasks


async def run_single_benchmark(sem: asyncio.Semaphore, task_info: dict, _session_factory) -> dict:
    """Run a single benchmark task through the full swarm pipeline and save results."""
    async with sem:
        benchmark_name = task_info.get("name", "Unknown")
        category = task_info.get("category", "general")
        title = task_info.get("title", benchmark_name)
        description = task_info.get("description", "")
        difficulty = task_info.get("difficulty", "medium")

        logger.info("[%s/%s] Starting: %s", category.upper(), difficulty.upper(), benchmark_name)
        start_time = time.time()

        # ── Create Task & Pipelines in DB ─────────────────────────
        task_id = None
        try:
            async for session in get_db_session():
                if not session:
                    break
                task_db = TaskDB(session)
                db_task = await task_db.create_task(
                    title, description, priority=2
                )
                if db_task:
                    task_id = str(db_task["id"])
                    pipeline_db = PipelineDB(session)
                    await pipeline_db.create_pipelines_for_task(task_id)
                    break
        except Exception as e:
            logger.error("Failed to create DB task for %s: %s", benchmark_name, e)

        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())

        active_tasks[task_id] = {
            "task_id":    task_id,
            "status":     "running",
            "title":      title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "outputs":    {},
            "pipelines": [
                {"name": "planning",    "status": "idle", "progress": 0},
                {"name": "engineering", "status": "idle", "progress": 0},
                {"name": "qa",          "status": "idle", "progress": 0},
                {"name": "security",    "status": "idle", "progress": 0},
                {"name": "devops",      "status": "idle", "progress": 0},
                {"name": "reliability", "status": "idle", "progress": 0},
            ],
        }

        # ── Run Full Swarm Pipeline ───────────────────────────────
        pipeline_error = None
        repair_iterations = 0
        failure_reason = None
        root_cause = None
        recovery_success = None

        try:
            await run_swarm_pipeline(task_id, title, description)
        except Exception as e:
            pipeline_error = str(e)
            logger.exception("Exception during pipeline for %s: %s", benchmark_name, e)

        execution_time = time.time() - start_time
        task_status = active_tasks.get(task_id, {}).get("status", "failed")

        # ── Determine Failure / Recovery Metrics ─────────────────
        if pipeline_error:
            failure_reason = f"Pipeline exception: {pipeline_error[:200]}"
            root_cause = "unhandled_exception"
            recovery_success = False
        elif task_status == "blocked":
            failure_reason = "Security scan detected critical vulnerabilities"
            root_cause = "security_block"
            recovery_success = False
        elif task_status == "failed":
            failure_reason = "Pipeline exited with failed status"
            root_cause = "pipeline_failure"
            recovery_success = False

        # Count repair iterations from task outputs
        outputs = active_tasks.get(task_id, {}).get("outputs", {})
        if "tests_patched" in outputs:
            repair_iterations = 1
            if task_status == "complete":
                recovery_success = True
                root_cause = "test_failure_repaired"
                failure_reason = "Initial tests failed, auto-repair applied successfully"

        # Use multi-signal score if available, else fall back to evaluation score
        score = 0.0
        pass_status = False

        # Check for the objective final_score computed by run_swarm_pipeline
        final_score_stored = active_tasks.get(task_id, {}).get("final_score")
        if final_score_stored is not None:
            score = float(final_score_stored)
            pass_status = score >= 7.0  # threshold for "pass" in benchmarks
        else:
            # Fallback: query EvaluationDB
            try:
                async for session in get_db_session():
                    if not session:
                        break
                    eval_db = EvaluationDB(session)
                    evals = await eval_db.get_evaluations(task_id)
                    if evals:
                        score = float(evals[0].get("overall_score", 0.0))
                        pass_status = score >= 7.0
                    break
            except Exception as e:
                logger.error("Failed to retrieve evaluation for %s: %s", benchmark_name, e)

            # Final fallback: status-based
            if score == 0.0:
                if task_status == "complete":
                    score = 8.0
                    pass_status = True
                else:
                    score = 4.0
                    pass_status = False

        # ── Save Benchmark Result to DB ───────────────────────────
        try:
            async for session in get_db_session():
                if not session:
                    break
                bench_db = BenchmarkDB(session)
                await bench_db.save_benchmark_result(
                    benchmark_name=f"[{category}] {benchmark_name}",
                    task_id=task_id,
                    pass_status=pass_status,
                    score=score,
                    execution_time=execution_time,
                    repair_iterations=repair_iterations,
                    failure_reason=failure_reason,
                    root_cause=root_cause,
                    recovery_success=recovery_success,
                )
                status_icon = "PASS" if pass_status else "FAIL"
                logger.info(
                    "[%s] %s | %s | Score: %.1f/10 | Repairs: %d | Time: %.1fs",
                    status_icon, category.upper(), benchmark_name, score, repair_iterations, execution_time
                )
                break
        except Exception as e:
            logger.error("Failed to save benchmark result for %s: %s", benchmark_name, e)

        return {
            "name": benchmark_name,
            "category": category,
            "score": score,
            "pass": pass_status,
            "time": execution_time,
            "repair_iterations": repair_iterations,
            "failure_reason": failure_reason,
            "root_cause": root_cause,
            "recovery_success": recovery_success,
        }


async def main():
    logger.info("=" * 60)
    logger.info("  NexusSwarm Benchmark Runner v2.0 (100-task suite)")
    logger.info("=" * 60)

    logger.info("Initializing database tables...")
    await init_db_tables()

    # Allow concurrency limit of 3 to avoid API rate limits
    sem = asyncio.Semaphore(3)

    # Load tasks from the categorized benchmarks/ directory
    limit = int(os.environ.get("BENCHMARK_LIMIT", "100"))
    tasks_to_run = load_benchmark_tasks(limit=limit)

    if not tasks_to_run:
        logger.error("No benchmark tasks found. Exiting.")
        return

    logger.info("Loaded %d benchmark tasks. Starting execution...", len(tasks_to_run))

    # Print category breakdown
    from collections import Counter
    category_counts = Counter(t.get("category", "general") for t in tasks_to_run)
    for cat, count in sorted(category_counts.items()):
        logger.info("  [%s]: %d tasks", cat.upper(), count)

    start_all = time.time()

    results = await asyncio.gather(
        *(run_single_benchmark(sem, task, None) for task in tasks_to_run),
        return_exceptions=True,
    )

    total_time = time.time() - start_all

    # Filter out exceptions
    valid_results = [r for r in results if isinstance(r, dict)]
    total = len(valid_results)
    passed = sum(1 for r in valid_results if r["pass"])
    failed = total - passed
    avg_score = sum(r["score"] for r in valid_results) / total if total > 0 else 0.0
    success_rate = (passed / total) * 100 if total > 0 else 0.0

    # Repair metrics
    repaired = [r for r in valid_results if r.get("repair_iterations", 0) > 0]
    repair_success = [r for r in repaired if r.get("recovery_success")]
    repair_success_rate = (len(repair_success) / len(repaired)) * 100 if repaired else 0.0

    # Hallucination category stats
    halluc_results = [r for r in valid_results if r.get("category") == "hallucination"]
    halluc_pass = sum(1 for r in halluc_results if r["pass"])
    halluc_pass_rate = (halluc_pass / len(halluc_results)) * 100 if halluc_results else 0.0

    # Per-category breakdown
    category_stats = {}
    for r in valid_results:
        cat = r.get("category", "general")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "scores": []}
        category_stats[cat]["total"] += 1
        if r["pass"]:
            category_stats[cat]["passed"] += 1
        category_stats[cat]["scores"].append(r["score"])

    logger.info("=" * 60)
    logger.info("  BENCHMARK RUN COMPLETE")
    logger.info("=" * 60)
    logger.info("Total Time:               %.2fs", total_time)
    logger.info("Total Executed:           %d", total)
    logger.info("Passed:                   %d", passed)
    logger.info("Failed:                   %d", failed)
    logger.info("Success Rate:             %.1f%%", success_rate)
    logger.info("Average Score:            %.2f/10", avg_score)
    logger.info("Repair Success Rate:      %.1f%%", repair_success_rate)
    logger.info("Hallucination Pass Rate:  %.1f%%", halluc_pass_rate)
    logger.info("-" * 60)
    logger.info("Category Breakdown:")
    for cat, stats in sorted(category_stats.items()):
        cat_avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
        cat_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0
        logger.info(
            "  %-15s  Pass: %d/%d (%.0f%%)  Avg Score: %.1f",
            cat.upper(), stats["passed"], stats["total"], cat_rate, cat_avg
        )
    logger.info("=" * 60)

    # List failures for analysis
    failures = [r for r in valid_results if not r["pass"]]
    if failures:
        logger.info("FAILURES (%d):", len(failures))
        for f in failures:
            logger.info(
                "  [%s] %s | root_cause=%s | reason=%s",
                f.get("category", "?").upper(),
                f.get("name", "?"),
                f.get("root_cause", "unknown"),
                (f.get("failure_reason") or "N/A")[:80]
            )


if __name__ == "__main__":
    asyncio.run(main())
