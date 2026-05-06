import ctypes
import sys
print("testing ctypes load...", flush=True)
try:
    lib = ctypes.WinDLL(r".\.venv\Lib\site-packages\greenlet\_greenlet.cp314-win_amd64.pyd")
    print("ctypes load ok", flush=True)
except Exception as e:
    print(f"ctypes error: {e}", flush=True)
print("done ctypes, now import greenlet", flush=True)
import greenlet
print("greenlet imported ok", flush=True)
sys.exit(0)
