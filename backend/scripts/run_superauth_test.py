import os
import sys
import asyncio
import logging

# Ensure backend is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from db.benchmark_loader import load_benchmark_tasks
from scripts.run_benchmarks import run_single_benchmark
from memory.db_client import init_db_tables

async def main():
    print("=" * 70)
    print("RUNNING THE 'ONE TEST I'D RUN FIRST': SUPERAUTH HALLUCINATION TRAP")
    print("=" * 70)
    
    print("Initializing database...")
    await init_db_tables()
    
    print("Loading adversarial tasks...")
    tasks = load_benchmark_tasks(100)
    superauth_task = None
    for t in tasks:
        if t.get("name") == "SuperAuth Enterprise Hallucination Trap":
            superauth_task = t
            break
            
    if not superauth_task:
        print("ERROR: SuperAuth task not found in loaded tasks!")
        return
        
    print(f"Found Task: {superauth_task.get('name')}")
    print(f"Title: {superauth_task.get('title')}")
    print(f"Description: {superauth_task.get('description')}")
    print("-" * 70)
    
    # Run task with concurrency=1
    sem = asyncio.Semaphore(1)
    
    print("Starting pipeline execution via NVIDIA NIM...")
    result = await run_single_benchmark(sem, superauth_task, None)
    
    print("=" * 70)
    print("EVALUATION RESULT")
    print("=" * 70)
    import json
    print(json.dumps(result, indent=2))
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
