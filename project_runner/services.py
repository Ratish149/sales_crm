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
        for port in range(3000, 3011):
            if not self.is_port_in_use(port):
                return port
        raise Exception("No free ports available in range 3000–3010")

    # --------------------------
    # MAIN RUNNER
    # --------------------------
    # --------------------------
    # MAIN RUNNER
    # --------------------------
    def add_caddy_route(self, host, port):
        """
        Dynamically adds a route to Caddy:
        host -> localhost:port
        """

        route_id = f"route_{self.workspace_id}"

        # Caddy JSON Config for a new route
        # Using the standard "reverse_proxy" handler
        # We append to the existing routes in the :3000 server
        # Note: This is a simplified approach using Caddy's /config/ endpoint

        # However, simpler approach for "add/remove" is using /id/ API if we set IDs.
        # But we started with a simplistic Caddyfile which is harder to patch via JSON.
        # BETTER: Use Caddy's /load API or just /config/apps/http/servers/srv0/routes

        # Let's try the simplest: PUT to /config/apps/http/servers/srv0/routes/...
        # But we don't know the exact structure of the Caddyfile adapter output.

        # FALLBACK: We will assume Caddy is running with a config that allows dynamic updates?
        # No, Caddyfile adapter is read-only.
        # FIX: We will use the 'caddy-api' to ADD a route.
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
                # Ensure Caddy route exists (idempotent)
                self.configure_caddy(host, port)

                # Update URL if host changed
                if host:
                    url = f"https://{host}"  # HTTPS handled by Traefik/Coolify
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
            subprocess.run("npm install", shell=True, cwd=self.project_path, check=True)

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
        self.configure_caddy(host, port)

        # URL construction
        # Now it is purely the subdomain, no port
        if host:
            url = f"https://{host}"
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

    def configure_caddy(self, host, port):
        """
        Sends configuration to Caddy Sidecar
        """
        if not host:
            return

        import requests

        # We use Caddy's dynamic config API to map:
        # Host: <host> -> Reverse Proxy: localhost:<port>

        # Caddy API endpoint for adding a route
        # We need to construct a JSON route object
        # This is complex without a base config.
        # SIMPLIFICATION:
        # We will assume a base config created by Python that listens on :3000.

        caddy_url = "http://localhost:2019/config/apps/http/servers/srv0/routes"

        # Check if route already exists? proper way is giving it an ID
        route_id = f"route_{self.workspace_id}"

        payload = {
            "@id": route_id,
            "match": [{"host": [host]}],
            "handle": [
                {
                    "handler": "reverse_proxy",
                    "upstreams": [{"dial": f"127.0.0.1:{port}"}],
                }
            ],
        }

        # We PUT to the ID to create or update
        try:
            requests.put(f"http://localhost:2019/id/{route_id}", json=payload)
            print(f"Caddy configured: {host} -> {port}")
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

            return True, "Stopped successfully"

        except Exception as e:
            return False, str(e)
