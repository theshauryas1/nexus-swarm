"""
benchmark_loader.py — NexusSwarm Benchmark Suite Loader
Recursively loads 100 benchmark tasks from the backend/benchmarks/ directory.
Tasks are organized into category folders, each containing JSON task files.
"""

import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

BENCHMARKS_DIR = os.path.join(os.path.dirname(__file__), "..", "benchmarks")


def load_benchmark_tasks(limit: int = 100) -> List[Dict]:
    """
    Recursively discover and load all benchmark JSON files from the benchmarks/ directory.
    Each file should be a JSON object: {"name": ..., "title": ..., "description": ..., "category": ...}
    or a JSON array of such objects.
    Returns a flat list sorted by category then name, up to `limit` entries.
    """
    all_tasks = []
    benchmarks_path = os.path.abspath(BENCHMARKS_DIR)

    if not os.path.isdir(benchmarks_path):
        logger.warning("Benchmarks directory not found: %s. Falling back to legacy BENCHMARK_TASKS.", benchmarks_path)
        try:
            from db.benchmark_tasks import BENCHMARK_TASKS
            return BENCHMARK_TASKS[:limit]
        except ImportError:
            return []

    # Walk all subdirectories
    for category_dir in sorted(os.listdir(benchmarks_path)):
        cat_path = os.path.join(benchmarks_path, category_dir)
        if not os.path.isdir(cat_path):
            continue
        for filename in sorted(os.listdir(cat_path)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(cat_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Support both single-task and multi-task (array) JSON files
                if isinstance(data, list):
                    for task in data:
                        task.setdefault("category", category_dir)
                        all_tasks.append(task)
                elif isinstance(data, dict):
                    data.setdefault("category", category_dir)
                    all_tasks.append(data)
            except Exception as e:
                logger.error("Failed to load benchmark file %s: %s", filepath, e)

    if not all_tasks:
        logger.warning("No benchmark tasks loaded from %s. Falling back to legacy BENCHMARK_TASKS.", benchmarks_path)
        try:
            from db.benchmark_tasks import BENCHMARK_TASKS
            return BENCHMARK_TASKS[:limit]
        except ImportError:
            return []

    logger.info("Loaded %d benchmark tasks from %s (limit=%d)", len(all_tasks), benchmarks_path, limit)
    return all_tasks[:limit]
