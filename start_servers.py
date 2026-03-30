import subprocess
import os
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_backend():
    print("Starting Flask Backend on port 5000...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "backend", "app.py")], cwd=os.path.join(BASE_DIR, "backend"))

def run_frontend():
    print("Starting Frontend on port 8000...")
    subprocess.run([sys.executable, "-m", "http.server", "8000"], cwd=os.path.join(BASE_DIR, "frontend"))

if __name__ == '__main__':
    t1 = threading.Thread(target=run_backend)
    t2 = threading.Thread(target=run_frontend)
    t1.start()
    t2.start()
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("Shutting down servers.")
        sys.exit(0)
