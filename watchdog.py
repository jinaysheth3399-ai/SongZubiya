"""Watchdog: keeps the uvicorn backend alive and auto-retries SSL/Drive failures."""
import subprocess
import sys
import time
import urllib.request
import json

BACKEND_URL = "http://127.0.0.1:8000"
VENV_PYTHON = r".venv\Scripts\python.exe"

def is_alive():
    try:
        urllib.request.urlopen(f"{BACKEND_URL}/api/status", timeout=5)
        return True
    except Exception:
        return False

def start_backend():
    print("Starting backend...", flush=True)
    proc = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=open("logs/backend_stdout.txt", "a"),
        stderr=open("logs/backend_stderr.txt", "a"),
    )
    time.sleep(7)
    return proc

def start_runner():
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/api/start", method="POST")
        urllib.request.urlopen(req, timeout=5)
        print("Runner started.", flush=True)
    except Exception as e:
        print(f"Runner start failed: {e}", flush=True)

def retry_failed():
    try:
        data = urllib.request.urlopen(f"{BACKEND_URL}/api/songs", timeout=8).read()
        songs = json.loads(data)
        failed = [s["id"] for s in songs if "Failed" in s.get("status", "")]
        if failed:
            print(f"Retrying {len(failed)} failed songs...", flush=True)
            for sid in failed:
                try:
                    urllib.request.urlopen(
                        urllib.request.Request(f"{BACKEND_URL}/api/retry/{sid}", method="POST"),
                        timeout=3
                    )
                except Exception:
                    pass
    except Exception:
        pass

def get_status():
    try:
        data = urllib.request.urlopen(f"{BACKEND_URL}/api/status", timeout=5).read()
        return json.loads(data)
    except Exception:
        return {}

import os
os.makedirs("logs", exist_ok=True)

backend_proc = None
if not is_alive():
    backend_proc = start_backend()
    start_runner()
else:
    print("Backend already running.", flush=True)
    start_runner()

check_interval = 30
last_retry = 0

while True:
    time.sleep(check_interval)

    if not is_alive():
        print("Backend died — restarting...", flush=True)
        if backend_proc:
            try:
                backend_proc.kill()
            except Exception:
                pass
        backend_proc = start_backend()
        start_runner()
        retry_failed()
        continue

    status = get_status()
    completed = status.get("completed", 0)
    total = status.get("total_songs", 195)
    failed = status.get("failed", 0)
    is_running = status.get("runner", {}).get("is_running", False)

    print(f"[{completed}/{total}] failed={failed} runner={is_running}", flush=True)

    now = time.time()
    if failed > 0 and now - last_retry > 60:
        retry_failed()
        last_retry = now

    if not is_running and completed < total:
        print("Runner stopped — restarting...", flush=True)
        start_runner()

    if completed >= total:
        print("All done!", flush=True)
        break
