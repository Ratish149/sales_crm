import json
import os

import requests
from django.conf import settings

from builder.file_service import FileService


class GitHubService:
    @staticmethod
    def create_repo(repo_name, description=""):
        token = settings.GITHUB_TOKEN
        if not token:
            print("GitHubService: No GITHUB_TOKEN set.")
            return None

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        url = "https://api.github.com/user/repos"

        # Try to create repo, append suffix if exists
        max_retries = 5
        base_name = repo_name

        for i in range(max_retries + 1):
            current_name = base_name if i == 0 else f"{base_name}-{i}"

            payload = {
                "name": current_name,
                "description": description,
                "private": False,
                "auto_init": True,  # Initialize with README so we can clone it
            }

            print(f"GitHubService: Creating repo '{current_name}'...")
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 201:
                data = response.json()
                clone_url = data.get("clone_url")
                print(f"GitHubService: Created {clone_url}")
                return clone_url

            elif response.status_code == 422:
                print(
                    f"GitHubService: Repo '{current_name}' already exists. Retrying..."
                )
                continue  # Try next suffix

            else:
                # Other error
                print(
                    f"GitHubService: Failed to create repo: {response.status_code} {response.text}"
                )
                return None

        print("GitHubService: Failed to create repo after retries.")
        return None

    @staticmethod
    def initialize_nextjs_project(repo_url, workspace_id):
        """
        Clones a template repo, updates package.json, and pushes to the new repo.
        """
        token = settings.GITHUB_TOKEN
        # Use a default template if not provided in environment
        template_repo_url = os.getenv(
            "TEMPLATE_REPO_URL", "https://github.com/nepdora-nepal/template.git"
        )

        if not token or not repo_url:
            return False

        print(
            f"GitHubService: Initializing Next.js project for {workspace_id} from {template_repo_url}"
        )
        fs = FileService(workspace_id)

        try:
            # 1. Clone Template
            fs.clone_repo(template_repo_url, token)

            # 2. Update package.json
            package_path = "package.json"
            try:
                content = fs.read_file(package_path)
                data = json.loads(content)
                data["name"] = str(workspace_id)
                fs.write_file(package_path, json.dumps(data, indent=2))
            except Exception as e:
                print(f"GitHubService: Could not update package.json: {e}")

            # 3. Change Remote and Push
            # FileService.push_changes pushes to "origin".
            # We need to change "origin" from template_url to repo_url first.

            import git

            repo = git.Repo(fs.base_path)

            # Remove existing origin (pointing to template)
            if "origin" in repo.remotes:
                repo.delete_remote("origin")

            # Add new origin (pointing to new empty repo)
            final_url = repo_url
            if token and "github.com" in repo_url:
                parts = repo_url.split("://")
                if len(parts) == 2:
                    final_url = f"{parts[0]}://{token}@{parts[1]}"

            repo.create_remote("origin", final_url)

            # 4. Push
            # We used fs.push_changes before, but that assumes "origin" is set.
            # It also handles cleanup. Let's use it, as it does `repo.remote(name="origin")`.
            # But wait, `push_changes` re-instantiates `git.Repo`.
            # Changing remote persists on disk, so it should be fine.

            del repo  # Release lock if any?

            fs.push_changes("Initialize from template", token, force=True)
            return True

        except Exception as e:
            print(f"GitHubService: Init failed: {e}")
            return False
