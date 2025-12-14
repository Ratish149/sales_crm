import json
import os
import socket
import subprocess
import sys

import requests  # <--- ADD THIS IMPORT
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
        for port in range(3000, 3011):
            if not self.is_port_in_use(port):
                return port
        raise Exception("No free ports available in range 3000–3010")

    # --------------------------
    # MAIN RUNNER
    # --------------------------
    # Placeholder function (not used in run_project)
    def add_caddy_route(self, host, port):
        pass

    def run_project(self, host=None):
        if not self.project_path.exists():
            raise FileNotFoundError(f"Workspace path not found: {self.project_path}")

        processes = load_processes()

        # Check if already running
        if self.workspace_id in processes:
            proc_info = processes[self.workspace_id]
            pid = proc_info.get("pid")
            port = proc_info.get("port")
            url = proc_info.get("url")

            # Validate process
            if self.is_process_running(pid):
                target_host = None
                if host:
                    clean_host = host.split(":")[0]
                    target_host = f"{self.workspace_id}.{clean_host}"

                    # Ensure Caddy route exists (idempotent)
                    self.configure_caddy(target_host, port)

                    # Update URL
                    url = f"https://{target_host}"
                    proc_info["url"] = url
                    processes[self.workspace_id] = proc_info
                    save_processes(processes)

                return {
                    "port": port,
                    "url": url,
                    "pid": pid,
                }
            else:
                print(f"Dead process {pid} found. Cleaning.")
                del processes[self.workspace_id]
                save_processes(processes)

        # Install dependencies
        if not (self.project_path / "node_modules").exists():
            print(f"Installing dependencies for {self.workspace_id}...")
            result = subprocess.run(
                "npm install", shell=True, cwd=self.project_path, check=False
            )
            if result.returncode != 0:
                print(f"Warning: npm install failed with code {result.returncode}")
                # Continue anyway - might work with existing modules

        subprocess.run(
            "npm install --save-dev @types/react @types/node",
            shell=True,
            cwd=self.project_path,
            check=False,
        )

        # Allocate INTERNAL port (4000+)
        # We use find_free_port but we need a new range that is NOT exposed
        port = self.find_free_internal_port()
        print(f"Starting next dev on INTERNAL port {port}")

        log_out = open(self.log_file, "a")

        # Bind to 127.0.0.1 (Internal only)
        # Caddy will proxy to this.
        cmd = f"npx next dev -p {port} -H 127.0.0.1"

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        else:
            kwargs["start_new_session"] = True

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=self.project_path,
            stdout=log_out,
            stderr=log_out,
            **kwargs,
        )

        # Configure Caddy (The Magic)
        # We want to route <workspace_id>.<base_host> -> localhost:<port>
        target_host = None
        if host:
            clean_host = host.split(":")[0]
            # Construct subdomain: workspace_id.clean_host
            # e.g. ip-store.admin.nepdora.com
            target_host = f"{self.workspace_id}.{clean_host}"
            self.configure_caddy(target_host, port)

        # URL construction
        if target_host:
            url = f"https://{target_host}"
        else:
            url = f"http://localhost:{port}"  # Fallback

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

    def find_free_internal_port(self):
        # Scan 4000-5000
        for port in range(4000, 5000):
            if not self.is_port_in_use(port):
                return port
        raise Exception("No free internal ports")

    # --------------------------
    # CORRECTED CADDY CONFIGURATION
    # --------------------------
    # --------------------------
    # CORRECTED CADDY CONFIGURATION
    # --------------------------
    def configure_caddy(self, host, port):
        """
        Idempotently configures Caddy:
        1. Tries PUT (update) by ID.
        2. If 404 (route not found), performs POST (insert) to /routes/0.
        """
        if not host:
            return

        print(f"DEBUG: configure_caddy called for {host} -> {port}")
        route_id = f"route_{self.workspace_id}"
        target_dial = f"127.0.0.1:{port}"
        base_url = "http://localhost:2019"

        # URL for idempotent creation/replacement of a route by ID
        id_url = f"{base_url}/id/{route_id}"
        # URL for inserting a new route at the top of the srv0 server
        routes_url = f"{base_url}/config/apps/http/servers/srv0/routes/0"

        route_payload = {
            "@id": route_id,
            "match": [{"host": [host]}],
            "handle": [
                {"handler": "reverse_proxy", "upstreams": [{"dial": target_dial}]}
            ],
            # Terminal means no other routes will be checked if this one matches
            "terminal": True,
        }

        try:
            # 1. ATTEMPT UPDATE (PUT): This will fail if the route is new (status 404)
            resp = requests.put(id_url, json=route_payload)

            if resp.status_code in (200, 201):
                print(
                    f"Caddy route '{host}' UPDATED successfully. Status: {resp.status_code}"
                )

            elif resp.status_code == 404:
                # 2. IF 404, ATTEMPT INSERT (POST) at the top of the route list
                print(f"Route {route_id} not found. Inserting new route at index 0...")
                resp = requests.post(routes_url, json=route_payload)

                if resp.status_code not in (200, 201):
                    print(
                        f"Caddy INSERT failed. Status: {resp.status_code}. Response: {resp.text}"
                    )
                else:
                    print(
                        f"Caddy route '{host}' INSERTED successfully. Status: {resp.status_code}"
                    )

            else:
                # Handle other unexpected errors
                print(
                    f"Caddy config failed: Status: {resp.status_code}. Response: {resp.text}"
                )

            # Optional debug check after operation
            debug_url = f"{base_url}/config/apps/http/servers/srv0/routes"
            debug_check = requests.get(debug_url)
            print(f"DEBUG: FULL ROUTES DUMP AFTER OPERATION: {debug_check.text}")

        except Exception as e:
            print(f"Failed to configure Caddy: {e}")

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

            # --- Caddy Cleanup (Recommended, though not strictly required for the fix) ---
            route_id = f"route_{self.workspace_id}"
            try:
                # DELETE the route upon stop
                requests.delete(f"http://localhost:2019/id/{route_id}")
                print(f"Caddy route {route_id} deleted successfully.")
            except Exception as e:
                print(f"Warning: Could not delete Caddy route {route_id}: {e}")
            # --------------------------------------------------------------------------

            return True, "Stopped successfully"

        except Exception as e:
            return False, str(e)
