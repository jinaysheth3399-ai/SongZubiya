import sys
import threading
import traceback
import time

# After 8 seconds, dump stack trace of all threads to a file
def dump_after_delay():
    time.sleep(8)
    with open(r"C:\Users\Victus\AppData\Local\Temp\hang_trace.txt", "w") as f:
        for thread_id, frame in sys._current_frames().items():
            f.write(f"\n=== Thread {thread_id} ===\n")
            traceback.print_stack(frame, file=f)
    sys.stdout.flush()

t = threading.Thread(target=dump_after_delay, daemon=True)
t.start()

print("starting import...", flush=True)
import sqlalchemy
print("import OK", flush=True)
