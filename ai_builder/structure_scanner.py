"""
Project Structure Scanner

Scans the project directory and returns structured information
about the project framework, file organization, and key files.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_framework(project_root: str) -> str:
    """
    Detect the framework being used in the project.

    Args:
        project_root: Root directory of the project

    Returns:
        Framework name: "nextjs-app-router", "nextjs-pages", "react", "vue", "other"
    """
    root_path = Path(project_root)

    # Check for Next.js
    if (root_path / "next.config.js").exists() or (
        root_path / "next.config.mjs"
    ).exists():
        # Check for app router vs pages router
        if (root_path / "app").exists() and (root_path / "app").is_dir():
            return "nextjs-app-router"
        elif (root_path / "pages").exists() and (root_path / "pages").is_dir():
            return "nextjs-pages"
        else:
            return "nextjs-app-router"  # Default to app router for new projects

    # Check for React
    package_json = root_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }

                if "react" in deps:
                    return "react"
                elif "vue" in deps:
                    return "vue"
        except Exception:
            pass

    return "other"


def scan_directory(
    path: Path,
    max_depth: int = 3,
    current_depth: int = 0,
    ignore_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Recursively scan directory and build structure dict.

    Args:
        path: Directory to scan
        max_depth: Maximum depth to scan
        current_depth: Current recursion depth
        ignore_dirs: Directories to ignore

    Returns:
        Dictionary representing directory structure
    """
    if ignore_dirs is None:
        ignore_dirs = [
            "node_modules",
            ".next",
            ".git",
            "dist",
            "build",
            "__pycache__",
            ".venv",
            "venv",
            "env",
        ]

    if current_depth >= max_depth:
        return {}

    structure = {}

    try:
        for item in sorted(path.iterdir()):
            # Skip ignored directories
            if item.name in ignore_dirs or item.name.startswith("."):
                continue

            if item.is_dir():
                # Recursively scan subdirectory
                substructure = scan_directory(
                    item, max_depth, current_depth + 1, ignore_dirs
                )
                if (
                    substructure or current_depth < 2
                ):  # Include empty dirs at shallow levels
                    structure[item.name] = substructure if substructure else {}
            else:
                # Mark as file
                structure[item.name] = "file"

    except PermissionError:
        pass

    return structure


def get_key_files(project_root: str, framework: str) -> List[str]:
    """
    Get list of key configuration files for the project.

    Args:
        project_root: Root directory
        framework: Detected framework

    Returns:
        List of key file names
    """
    root_path = Path(project_root)
    key_files = []

    # Common files
    common = ["package.json", "tsconfig.json", "README.md", ".env", ".env.local"]

    # Framework-specific files
    if "nextjs" in framework:
        framework_specific = [
            "next.config.js",
            "next.config.mjs",
            "tailwind.config.js",
            "tailwind.config.ts",
            "postcss.config.js",
        ]
    elif framework == "react":
        framework_specific = [
            "vite.config.js",
            "vite.config.ts",
            "webpack.config.js",
            "tailwind.config.js",
        ]
    else:
        framework_specific = []

    all_candidates = common + framework_specific

    for filename in all_candidates:
        if (root_path / filename).exists():
            key_files.append(filename)

    return key_files


def scan_project(project_root: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Scan project and return comprehensive structure information.

    Args:
        project_root: Root directory of the project
        max_depth: Maximum depth to scan

    Returns:
        {
            "framework": "nextjs-app-router",
            "root": "/path/to/project",
            "structure": {...},
            "key_files": [...]
        }
    """
    root_path = Path(project_root)

    if not root_path.exists():
        raise ValueError(f"Project root does not exist: {project_root}")

    framework = detect_framework(project_root)
    structure = scan_directory(root_path, max_depth=max_depth)
    key_files = get_key_files(project_root, framework)

    return {
        "framework": framework,
        "root": str(root_path),
        "structure": structure,
        "key_files": key_files,
    }


def format_structure_for_display(structure: Dict[str, Any], indent: int = 0) -> str:
    """
    Format structure dict as readable tree string.

    Args:
        structure: Structure dictionary
        indent: Current indentation level

    Returns:
        Formatted string representation
    """
    lines = []
    indent_str = "  " * indent

    for key, value in structure.items():
        if value == "file":
            lines.append(f"{indent_str}📄 {key}")
        elif isinstance(value, dict):
            lines.append(f"{indent_str}📁 {key}/")
            if value:  # Only recurse if not empty
                lines.append(format_structure_for_display(value, indent + 1))

    return "\n".join(lines)


def get_project_structure_summary(project_root: str) -> str:
    """
    Get a human-readable summary of the project structure.

    Args:
        project_root: Root directory of the project

    Returns:
        Formatted string describing the project
    """
    scan_result = scan_project(project_root, max_depth=3)

    summary = f"""Framework: {scan_result["framework"]}
Root: {scan_result["root"]}

Key Configuration Files:
{", ".join(scan_result["key_files"]) if scan_result["key_files"] else "None"}

Project Structure:
{format_structure_for_display(scan_result["structure"])}
"""

    return summary


def generate_file_tree(root_path: str, include_content: bool = True) -> Dict[str, Any]:
    """
    Generate a file tree compatible with the frontend builder.
    Include content by default.
    """
    base_path = Path(root_path)
    if not base_path.exists():
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
                # Calculate relative path
                try:
                    rel_path = str(Path(entry.path).relative_to(base_path)).replace(
                        "\\", "/"
                    )
                except ValueError:
                    # Should not happen given we are scanning children
                    continue

                item = {"name": entry.name, "path": rel_path}
                if entry.is_dir():
                    item["type"] = "folder"
                    item["children"] = build_tree(entry.path)
                else:
                    item["type"] = "file"
                    if include_content:
                        try:
                            # Limit file size reading if necessary, but for now read all text
                            with open(entry.path, "r", encoding="utf-8") as f:
                                item["content"] = f.read()
                        except (UnicodeDecodeError, IOError):
                            # Skip binary files or unreadable files
                            item["content"] = None
                items.append(item)
        except OSError:
            pass
        return items

    return {"action": "tree", "items": build_tree(base_path)}
