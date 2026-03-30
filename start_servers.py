import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0

def wait_for_port(port, label, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            print(f"{label} is ready on port {port}.")
            return True
        time.sleep(0.5)
    print(f"Timed out waiting for {label} on port {port}.")
    return False

def terminate_process(proc, label):
    if proc.poll() is not None:
        return
    print(f"Stopping {label}...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print(f"{label} did not stop in time. Killing it.")
        proc.kill()

def start_backend(port):
    env = os.environ.copy()
    env["BACKEND_PORT"] = str(port)
    print(f"Starting Flask backend on port {port}...")
    return subprocess.Popen(
        [sys.executable, os.path.join(BACKEND_DIR, "app.py")],
        cwd=BACKEND_DIR,
        env=env
    )

def start_frontend(port):
    print(f"Starting frontend on port {port}...")
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=FRONTEND_DIR
    )

def parse_args():
    parser = argparse.ArgumentParser(description="Start Society Hub frontend and backend servers.")
    parser.add_argument("--backend-port", type=int, default=5000, help="Port for the Flask backend.")
    parser.add_argument("--frontend-port", type=int, default=8000, help="Port for the static frontend server.")
    parser.add_argument("--open-browser", action="store_true", help="Open the resident portal after both servers are ready.")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.backend_port == args.frontend_port:
        print("Backend and frontend ports must be different.")
        sys.exit(1)

    for port, label in ((args.backend_port, "Backend"), (args.frontend_port, "Frontend")):
        if is_port_open(port):
            print(f"{label} port {port} is already in use. Choose a different port.")
            sys.exit(1)

    backend_proc = start_backend(args.backend_port)
    frontend_proc = start_frontend(args.frontend_port)

    try:
        backend_ready = wait_for_port(args.backend_port, "Backend")
        frontend_ready = wait_for_port(args.frontend_port, "Frontend")

        if args.open_browser and backend_ready and frontend_ready:
            webbrowser.open(f"http://127.0.0.1:{args.frontend_port}/index.html")

        print(f"Resident portal: http://127.0.0.1:{args.frontend_port}/index.html")
        print(f"Guard portal:    http://127.0.0.1:{args.frontend_port}/guard.html")
        print(f"Admin portal:    http://127.0.0.1:{args.frontend_port}/admin.html")
        print("Press Ctrl+C to stop both servers.")

        while True:
            if backend_proc.poll() is not None:
                print("Backend exited. Shutting down frontend.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend exited. Shutting down backend.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down servers.")
    finally:
        terminate_process(backend_proc, "backend")
        terminate_process(frontend_proc, "frontend")
        sys.exit(0)
