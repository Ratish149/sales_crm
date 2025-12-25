import os
import shutil
import stat
import time
from pathlib import Path

import git
from django.conf import settings


class FileService:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        # Adapt for multi-tenant if needed, but keeping simple for now
        self.base_path = settings.MEDIA_ROOT / "workspaces" / str(workspace_id)

    def _ensure_dir(self):
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, path):
        self._ensure_dir()
        clean_path = str(path).lstrip("/\\")
        full_path = (self.base_path / clean_path).resolve()
        if not str(full_path).startswith(str(self.base_path.resolve())):
            raise PermissionError("Access denied: Path traversal attempt detected.")
        return full_path

    def _force_delete(self, action, name, exc):
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    def _cleanup_workspace(self):
        if self.base_path.exists():
            print(f"FileService: Cleaning up {self.base_path}...")
            for i in range(3):
                try:
                    shutil.rmtree(self.base_path, onerror=self._force_delete)
                    break
                except Exception as e:
                    print(f"FileService: Cleanup attempt {i + 1} failed: {e}")
                    time.sleep(0.5)

            if self.base_path.exists():
                print("FileService: CRITICAL - Could not delete workspace.")
                del self.base_path  # try to unreference?
                import gc

                gc.collect()
                # Last ditch effort
                try:
                    shutil.rmtree(self.base_path, onerror=self._force_delete)
                except Exception:
                    raise OSError("Could not clean workspace. File locking issue.")
            else:
                print("FileService: Cleanup successful.")

    def clone_repo(self, repo_url, token=None):
        print(f"FileService: Cloning {repo_url} into {self.base_path}")

        try:
            self._cleanup_workspace()
        except OSError:
            raise Exception(
                "Cannot clean up previous workspace. Please wait or restart server."
            )

        final_url = repo_url
        if token and "github.com" in repo_url:
            parts = repo_url.split("://")
            if len(parts) == 2:
                final_url = f"{parts[0]}://{token}@{parts[1]}"

        try:
            git.Repo.clone_from(final_url, self.base_path)
            repo = git.Repo(self.base_path)
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", "Builder User")
                git_config.set_value("user", "email", "builder@example.com")
            print("FileService: Clone successful")
            return True
        except Exception as e:
            print(f"FileService: Clone failed: {e}")
            raise Exception(f"Clone failed: {str(e)}")

    def push_changes(self, message, token=None, force=False):
        print("FileService: Starting push sequence...")
        if not self.base_path.exists():
            print("FileService: Workspace does not exist")
            raise FileNotFoundError("Workspace does not exist.")

        try:
            repo = git.Repo(self.base_path)
            origin = repo.remote(name="origin")

            print("FileService: Git Add...")
            repo.git.add("--all")

            print("FileService: Committing...")
            try:
                repo.git.commit("-m", message or "Update from Builder")
            except git.GitCommandError as e:
                err_str = str(e).lower()
                if "nothing to commit" in err_str or "clean" in err_str:
                    print("FileService: Nothing to commit.")
                elif "unable to read tree" in err_str or "index" in err_str:
                    print("FileService: CORRUPTION DETECTED. Attempting repair...")
                    try:
                        index_file = self.base_path / ".git" / "index"
                        if index_file.exists():
                            os.remove(index_file)
                        print("FileService: Removed .git/index. Resetting...")
                        repo.git.reset()
                        repo.git.add("--all")
                        repo.git.commit("-m", message or "Update from Builder")
                    except Exception as repair_err:
                        print(f"FileService: Repair failed: {repair_err}")
                        raise e
                else:
                    raise e

            print("FileService: Pushing to origin...")
            # Use git command directly to ensure upstream is set
            current_branch = repo.active_branch.name
            args = ["--set-upstream", "origin", current_branch]
            if force:
                args.insert(0, "--force")

            repo.git.push(*args)
            print("FileService: Push successful.")

            del repo
            del origin
            import gc

            gc.collect()

            self._cleanup_workspace()

            return True
        except Exception as e:
            print(f"FileService: Push failed: {e}")
            raise Exception(f"Push failed: {str(e)}")

    def read_file(self, path):
        full_path = self._get_safe_path(path)
        if not full_path.exists() or not full_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path, content):
        full_path = self._get_safe_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def delete_file(self, path):
        full_path = self._get_safe_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if full_path.is_dir():
            import shutil

            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return True

    def create_directory(self, path):
        full_path = self._get_safe_path(path)
        if full_path.exists():
            raise FileExistsError(f"Directory already exists: {path}")
        full_path.mkdir(parents=True, exist_ok=True)
        return True

    def rename_file(self, old_path, new_path):
        old_full_path = self._get_safe_path(old_path)
        new_full_path = self._get_safe_path(new_path)

        if not old_full_path.exists():
            raise FileNotFoundError(f"File not found: {old_path}")

        if new_full_path.exists():
            raise FileExistsError(f"Destination already exists: {new_path}")

        # Ensure parent directory of new_path exists
        new_full_path.parent.mkdir(parents=True, exist_ok=True)

        os.rename(old_full_path, new_full_path)
        return True

    def upload_file(self, path, content):
        """
        Uploads a file to the workspace.
        If the path starts with 'public/', it allows saving there.
        Content is expected to be base64 encoded string.
        """
        import base64

        # For now, we force uploads to go to 'public/' if not already specified,
        # OR we just blindly trust the path but ensure it safely resolves inside workspace.
        # The prompt said "save to its tenant public folder".
        # So we should enforce 'public/' prefix or directory.

        if not path.startswith("public/"):
            path = f"public/{path}"

        full_path = self._get_safe_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Decode base64 content
            # The content might look like "data:image/png;base64,iVBORw0KGgo..."
            if "," in content:
                content = content.split(",")[1]

            decoded_content = base64.b64decode(content)

            with open(full_path, "wb") as f:
                f.write(decoded_content)
            return True
        except Exception as e:
            print(f"FileService: Upload failed: {e}")
            raise Exception(f"Upload failed: {str(e)}")

    def generate_tree(self, include_content=True):
        if not self.base_path.exists():
            return {"action": "tree", "items": []}

        IGNORED_DIRS = {
            ".git",
            "node_modules",
            "__pycache__",
            ".next",
            "venv",
            ".venv",
            "dist",
            "build",
            ".idea",
            ".vscode",
        }

        def build_tree(directory):
            items = []
            try:
                entries = sorted(
                    os.scandir(directory),
                    key=lambda e: (not e.is_dir(), e.name.lower()),
                )
                for entry in entries:
                    if entry.name in IGNORED_DIRS:
                        continue
                    rel_path = str(
                        Path(entry.path).relative_to(self.base_path)
                    ).replace("\\", "/")
                    item = {"name": entry.name, "path": rel_path}
                    if entry.is_dir():
                        item["type"] = "folder"
                        item["children"] = build_tree(entry.path)
                    else:
                        item["type"] = "file"
                        if include_content:
                            try:
                                with open(entry.path, "r", encoding="utf-8") as f:
                                    item["content"] = f.read()
                            except (UnicodeDecodeError, IOError):
                                # Skip binary files or unreadable files
                                item["content"] = None
                    items.append(item)
            except OSError:
                pass
            return items

        return {"action": "tree", "items": build_tree(self.base_path)}

    def update_image_map(self, image_id, relative_path):
        """
        Updates the images.json file with a new image mapping.
        """
        import json

        images_json_path = self.base_path / "images.json"

        data = {}
        if images_json_path.exists():
            try:
                with open(images_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"FileService: Error reading images.json: {e}")
                data = {}

        data[image_id] = relative_path

        try:
            with open(images_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"FileService: Error writing images.json: {e}")
            raise Exception(f"Failed to update image map: {str(e)}")
