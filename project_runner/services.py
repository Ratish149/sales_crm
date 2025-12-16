import json
import os
import socket
import subprocess
import sys

from django.conf import settings

# Path to persistent process store file
PROCESS_STORE_PATH = settings.MEDIA_ROOT / "running_projects.json"


# --------------------------
# JSON READ/WRITE HELPERS
# --------------------------
def load_processes():
    if not PROCESS_STORE_PATH.exists():
        return {}
    try:
        with open(PROCESS_STORE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_processes(processes):
    try:
        with open(PROCESS_STORE_PATH, "w") as f:
            json.dump(processes, f, indent=2)
    except IOError as e:
        print(f"Error saving process store: {e}")


# --------------------------
# RUNNER SERVICE
# --------------------------
class RunnerService:
    def __init__(self, workspace_id):
        self.workspace_id = str(workspace_id)
        self.project_path = settings.MEDIA_ROOT / "workspaces" / self.workspace_id
        self.log_file = self.project_path / "server.log"

    # --------------------------
    # Helpers
    # --------------------------
    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", int(port))) == 0

    def is_process_running(self, pid):
        if not pid:
            return False

        if sys.platform == "win32":
            try:
                cmd = f'tasklist /FI "PID eq {pid}" /NH'
                output = subprocess.check_output(cmd, shell=True).decode()
                return str(pid) in output
            except Exception:
                return False
        else:
            try:
                os.kill(int(pid), 0)
                return True
            except OSError:
                return False

    def find_free_port(self):
        for port in range(3000, 4000):
            if not self.is_port_in_use(port):
                return port
        raise Exception("No free ports available in range 3000–4000")

    # --------------------------
    # MAIN RUNNER
    # --------------------------
    def run_project(self):
        if not self.project_path.exists():
            raise FileNotFoundError(f"Workspace path not found: {self.project_path}")

        processes = load_processes()

        # Check if already running
        if self.workspace_id in processes:
            proc_info = processes[self.workspace_id]
            pid = proc_info.get("pid")
            port = proc_info.get("port")
            url = proc_info.get("url")

            if self.is_process_running(pid):
                return {
                    "port": port,
                    "url": url,
                    "pid": pid,
                }
            else:
                print(
                    f"Dead process {pid} found for workspace {self.workspace_id}. Cleaning."
                )
                del processes[self.workspace_id]
                save_processes(processes)

        # Install dependencies if needed
        if not (self.project_path / "node_modules").exists():
            print(f"Installing npm dependencies for workspace {self.workspace_id}...")
            subprocess.run("npm install", shell=True, cwd=self.project_path, check=True)

        # Always ensure types installed (prevents next.js prompt)
        subprocess.run(
            "npm install --save-dev @types/react @types/node",
            shell=True,
            cwd=self.project_path,
            check=False,
        )

        # Allocate port
        port = self.find_free_port()
        print(f"Starting next dev on port {port} for workspace {self.workspace_id}")

        # Prepare logs
        log_out = open(self.log_file, "a")

        cmd = f"npx next dev -p {port}"

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        else:
            kwargs["start_new_session"] = True

        # Launch process
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=self.project_path,
            stdout=log_out,
            stderr=log_out,
            **kwargs,
        )

        print("Process started with PID:", process.pid)
        print("Process started with command:", cmd)

        # --- IMPORTANT ---
        # For Coolify / Docker support: use SERVER_IP env var
        SERVER_IP = os.environ.get("SERVER_IP", "127.0.0.1")
        url = f"http://{SERVER_IP}:{port}"

        # Save process entry
        processes[self.workspace_id] = {
            "pid": process.pid,
            "port": port,
            "url": url,
        }
        save_processes(processes)

        return {
            "port": port,
            "url": url,
            "pid": process.pid,
        }

    # --------------------------
    # STOP RUNNER
    # --------------------------
    def stop_project(self):
        processes = load_processes()

        if self.workspace_id not in processes:
            return False, "Project is not running"

        proc_info = processes[self.workspace_id]
        pid = proc_info.get("pid")

        if not pid:
            del processes[self.workspace_id]
            save_processes(processes)
            return True, "Invalid process entry cleaned"

        try:
            if sys.platform == "win32":
                cmd = f"taskkill /F /T /PID {pid}"
                subprocess.run(cmd, shell=True, check=False)
            else:
                os.kill(int(pid), 9)

            del processes[self.workspace_id]
            save_processes(processes)

            return True, "Stopped successfully"

        except Exception as e:
            return False, str(e)
