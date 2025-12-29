import os
from pathlib import Path
from typing import Dict, List


class ProjectScanner:
    """Scans project structure and reads key files."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.ignore_dirs = {
            "node_modules",
            ".next",
            ".git",
            "dist",
            "build",
            "__pycache__",
            ".venv",
            "venv",
            ".idea",
            ".vscode",
        }
        self.ignore_files = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}

    def get_readme_content(self) -> str:
        """Reads the content of README.md if it exists."""
        readme_candidates = ["README.md", "readme.md", "README.txt", "README"]
        for name in readme_candidates:
            path = self.root_path / name
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    return f"Error reading README: {e}"
        return "No README.md found."

    def list_files(self, max_depth: int = 4) -> List[str]:
        """Lists all relevant files in the project."""
        file_list = []

        for root, dirs, files in os.walk(self.root_path):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [
                d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")
            ]

            # Check depth
            rel_dir = Path(root).relative_to(self.root_path)
            if len(rel_dir.parts) > max_depth:
                continue

            for file in files:
                if file in self.ignore_files or file.startswith("."):
                    continue

                # Filter by extension (optional, but good for focus)
                if file.endswith(
                    (".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf")
                ):
                    continue

                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.root_path)
                file_list.append(str(rel_path).replace("\\", "/"))

        return sorted(file_list)

    def read_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Reads content of specified files."""
        results = {}
        for rel_path in file_paths:
            full_path = self.root_path / rel_path
            if full_path.exists() and full_path.is_file():
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        results[rel_path] = f.read()
                except Exception as e:
                    results[rel_path] = f"Error reading file: {e}"
            else:
                results[rel_path] = "File not found."
        return results

    def scan_project_resources(self) -> str:
        """
        Scans src/hooks, src/services/api, and src/types to find available tools.
        Returns a formatted string for the LLM prompt.
        """
        src_path = self.root_path / "src"
        hooks_path = src_path / "hooks"
        services_path = src_path / "services" / "api"
        types_path = src_path / "types"

        summary_lines = ["## AVAILABLE PROJECT RESOURCES (STRICTLY USE THESE)"]

        # 1. Scan Types (CRITICAL for Data Shape)
        if types_path.exists():
            summary_lines.append("\n### Project Types (src/types/):")
            try:
                for item in sorted(types_path.glob("*.ts")):
                    if item.is_file():
                        try:
                            with open(item, "r", encoding="utf-8") as f:
                                content = f.read()
                                summary_lines.append(f"\n#### {item.name}")
                                summary_lines.append(f"```typescript\n{content}\n```")
                        except Exception:
                            pass
            except Exception as e:
                summary_lines.append(f"Error scanning types: {e}")

        # 2. Scan Hooks
        if hooks_path.exists():
            summary_lines.append("\n### Data Fetching Hooks (src/hooks/):")
            try:
                for item in sorted(hooks_path.glob("*.ts*")):
                    if item.is_file():
                        try:
                            with open(item, "r", encoding="utf-8") as f:
                                content = f.read()
                                summary_lines.append(f"\n#### {item.name}")
                                summary_lines.append(f"```typescript\n{content}\n```")
                        except Exception:
                            pass
            except Exception as e:
                summary_lines.append(f"Error scanning hooks: {e}")

        # 3. Scan Services
        if services_path.exists():
            summary_lines.append("\n### API Services (src/services/api/):")
            try:
                for item in sorted(services_path.glob("*.ts")):
                    if item.is_file():
                        try:
                            with open(item, "r", encoding="utf-8") as f:
                                content = f.read()
                                summary_lines.append(f"\n#### {item.name}")
                                summary_lines.append(f"```typescript\n{content}\n```")
                        except Exception:
                            pass
            except Exception:
                pass

        return "\n".join(summary_lines)
