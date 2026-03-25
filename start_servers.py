import subprocess
import os
import sys
import threading

def run_backend():
    print("Starting Flask Backend on port 5000...")
    os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))
    subprocess.run([sys.executable, "app.py"])

def run_frontend():
    print("Starting Frontend on port 8000...")
    os.chdir(os.path.join(os.path.dirname(__file__), 'frontend'))
    subprocess.run([sys.executable, "-m", "http.server", "8000"])

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
