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

    def configure_caddy(self, host, port):
        """
        Sends configuration to Caddy Sidecar - Idempotent

        MODIFICATION: Added www_host to the match list.
        """
        if not host:
            return

        import requests

        www_host = f"www.{host}"  # Define www version of the host

        print(f"DEBUG: configure_caddy called for {host} and {www_host} -> {port}")
        route_id = f"route_{self.workspace_id}"
        target_dial = f"127.0.0.1:{port}"

        # 1. OPTIMIZATION: Check if route already exists and is correct
        try:
            print(f"DEBUG: Checking if route {route_id} exists...")
            curr_resp = requests.get(f"http://localhost:2019/id/{route_id}")
            if curr_resp.status_code == 200:
                print(f"DEBUG: Route {route_id} exists. Checking config...")
                curr_config = curr_resp.json()

                # Check if it matches what we want
                try:
                    curr_dial = curr_config["handle"][0]["upstreams"][0]["dial"]

                    # Check for the correct host matching (either [host] or [host, www_host])
                    expected_hosts = [host, www_host]

                    # Attempt to extract hosts from the first match block
                    curr_hosts = []
                    if (
                        len(curr_config["match"]) >= 1
                        and "host" in curr_config["match"][0]
                    ):
                        curr_hosts = curr_config["match"][0]["host"]

                    # Check if the dial is correct AND the set of hosts is correct
                    if curr_dial == target_dial and sorted(curr_hosts) == sorted(
                        expected_hosts
                    ):
                        print(
                            f"DEBUG: Caddy route {route_id} correct. Skipping reload."
                        )
                        return
                    else:
                        print(
                            f"DEBUG: Route mismatch. Curr Dial: {curr_dial}, Target Dial: {target_dial}"
                        )
                        print(
                            f"DEBUG: Route mismatch. Curr Hosts: {curr_hosts}, Target Hosts: {expected_hosts}"
                        )

                except (KeyError, IndexError) as e:
                    print(f"DEBUG: Route structure mismatch during check: {e}")
                    pass  # Structure mismatch, proceed to update

                # If we are here, it exists but is different. Update in place.
                print(f"Updating existing Caddy route {route_id}...")
                route_payload = {
                    "@id": route_id,
                    # MODIFIED: Use the correct host match list and removed unnecessary X-Forwarded-Host header match
                    "match": [{"host": [host, www_host]}],
                    "handle": [
                        {
                            "handler": "reverse_proxy",
                            "upstreams": [{"dial": target_dial}],
                            "headers": {
                                "request": {
                                    "set": {"Host": ["{http.request.host}"]},
                                    # CRITICAL: Include HMR headers for Next.js live-reload
                                    "copy": ["Upgrade", "Connection"],
                                }
                            },
                        }
                    ],
                    "terminal": True,
                }
                resp = requests.post(
                    f"http://localhost:2019/id/{route_id}", json=route_payload
                )
                print(
                    f"DEBUG: Update payload sent. Response: {resp.status_code} {resp.text}"
                )

                # Validation: Dump config
                debug_check = requests.get(
                    "http://localhost:2019/config/apps/http/servers/srv0/routes"
                )
                print(f"DEBUG: FULL ROUTES DUMP: {debug_check.text}")
                return
            else:
                print(
                    f"DEBUG: Route {route_id} not found (Status {curr_resp.status_code})"
                )

        except Exception as e:
            print(f"Error checking Caddy route: {e}")

        # 2. If valid server not found? (Shouldn't happen with GET /id/)
        # We need to find the server to INSERT into if it's new.

        print(f"Adding new Caddy route {route_id}...")
        base_url = "http://localhost:2019/config/apps/http/servers"
        server_name = "srv0"

        try:
            r = requests.get(base_url)
            if r.status_code == 200:
                servers = r.json()
                for name, srv in servers.items():
                    if ":8000" in srv.get("listen", []):
                        server_name = name
                        break
        except Exception:
            pass

        # 3. Insert NEW route at the top
        routes_url = f"{base_url}/{server_name}/routes/0"

        route_payload = {
            "@id": route_id,
            "match": [{"host": [host, www_host]}],  # MODIFIED: Include both hosts
            "handle": [
                {"handler": "reverse_proxy", "upstreams": [{"dial": target_dial}]}
            ],
            "terminal": True,
        }

        try:
            resp = requests.put(routes_url, json=route_payload)
            if resp.status_code != 200:
                print(f"Caddy config failed: {resp.text}")
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
