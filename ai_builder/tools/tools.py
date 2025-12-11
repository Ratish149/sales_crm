"""
AI Builder Tools Module

This module contains all the tools that the AI agent can use.
Each tool has a clear signature and returns structured data.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# ============================================================================
# FILE OPERATION TOOLS
# ============================================================================


def list_files(
    path: str = "",
    glob_pattern: str = "*",
    ignore: List[str] = None,
    max_depth: int = None,
) -> Dict[str, Any]:
    """
    Lists files and directories in the repository.

    Args:
        path: Directory path to list (absolute or relative to project root)
        glob_pattern: Glob pattern to filter files (e.g., '*.py', '*.{js,jsx}')
        ignore: List of glob patterns to ignore
        max_depth: Maximum depth to traverse

    Returns:
        {
            "status": "success",
            "files": [{"path": "...", "type": "file|dir", "size": ...}, ...],
            "total_count": 10
        }
    """
    try:
        target_path = Path(path) if path else Path.cwd()

        if not target_path.exists():
            return {"status": "error", "message": f"Path does not exist: {path}"}

        files = []
        ignore = ignore or []

        # Use rglob for recursive search
        pattern = glob_pattern or "*"
        for item in target_path.rglob(pattern):
            # Check ignore patterns
            if any(item.match(ig) for ig in ignore):
                continue

            # Check max depth
            if max_depth is not None:
                relative_depth = len(item.relative_to(target_path).parts)
                if relative_depth > max_depth:
                    continue

            files.append(
                {
                    "path": str(item.relative_to(target_path)),
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )

        return {
            "status": "success",
            "files": sorted(files, key=lambda x: x["path"]),
            "total_count": len(files),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def read_file(
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reads file contents intelligently.

    Args:
        file_path: Path to the file
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        query: Optional query to find relevant chunks in large files

    Returns:
        {
            "status": "success",
            "content": "file content...",
            "total_lines": 150,
            "returned_lines": "1-150"
        }
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        if not path.is_file():
            return {"status": "error", "message": f"Not a file: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Apply line range if specified
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else total_lines
            lines = lines[start:end]
            returned_range = f"{start + 1}-{min(end, total_lines)}"
        else:
            # Default: return first 500 lines for large files
            if total_lines > 500:
                lines = lines[:500]
                returned_range = (
                    "1-500 (file is larger, use start_line/end_line for more)"
                )
            else:
                returned_range = f"1-{total_lines}"

        content = "".join(lines)

        return {
            "status": "success",
            "content": content,
            "total_lines": total_lines,
            "returned_lines": returned_range,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_files(
    pattern: str, path: str = "", glob_pattern: str = "*", case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Regex-based code search across files.

    Args:
        pattern: Regex pattern to search for
        path: Directory to search in
        glob_pattern: Files to include (e.g., '*.py', '*.{js,jsx}')
        case_sensitive: Whether to match case

    Returns:
        {
            "status": "success",
            "matches": [
                {"file": "...", "line": 10, "content": "...", "match": "..."},
                ...
            ],
            "total_matches": 5
        }
    """
    try:
        target_path = Path(path) if path else Path.cwd()

        if not target_path.exists():
            return {"status": "error", "message": f"Path does not exist: {path}"}

        # Compile regex
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        matches = []

        # Search in files
        for file_path in target_path.rglob(glob_pattern):
            if not file_path.is_file():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        match = regex.search(line)
                        if match:
                            matches.append(
                                {
                                    "file": str(file_path.relative_to(target_path)),
                                    "line": line_num,
                                    "content": line.rstrip(),
                                    "match": match.group(0),
                                }
                            )

                        # Limit to 200 matches
                        if len(matches) >= 200:
                            break
            except Exception:
                # Skip files that cannot be read
                continue

        return {"status": "success", "matches": matches, "total_matches": len(matches)}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a file (creates or overwrites).

    Args:
        file_path: Path to the file
        content: Content to write

    Returns:
        {"status": "success", "message": "File written successfully"}
    """
    try:
        path = Path(file_path)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"File written: {file_path}",
            "lines_written": len(content.split("\n")),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def delete_file(file_path: str) -> Dict[str, Any]:
    """
    Deletes a file.

    Args:
        file_path: Path to the file to delete

    Returns:
        {"status": "success", "message": "File deleted"}
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        if not path.is_file():
            return {"status": "error", "message": f"Not a file: {file_path}"}

        path.unlink()

        return {"status": "success", "message": f"Deleted file: {file_path}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def replace_in_file(
    file_path: str, search: str, replace: str, first_line: int, last_line: int
) -> Dict[str, Any]:
    """
    Line-based search and replace in a file.

    Args:
        file_path: Path to the file
        search: Content to search for (can use ... for ellipsis)
        replace: Replacement content
        first_line: First line number to replace (1-indexed)
        last_line: Last line number to replace (1-indexed)

    Returns:
        {"status": "success", "message": "..."}
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Validate line range
        if first_line < 1 or last_line > len(lines) or first_line > last_line:
            return {
                "status": "error",
                "message": f"Invalid line range: {first_line}-{last_line} (file has {len(lines)} lines)",
            }

        # Extract target section
        target_lines = lines[first_line - 1 : last_line]
        target_content = "".join(target_lines)

        # Handle ellipsis in search
        if "..." in search:
            # Simple ellipsis support: just check prefix and suffix
            parts = search.split("...")
            if len(parts) == 2:
                prefix, suffix = parts
                if not (
                    target_content.startswith(prefix)
                    and target_content.endswith(suffix)
                ):
                    return {
                        "status": "error",
                        "message": "Search pattern with ellipsis does not match target section",
                    }
        else:
            # Exact match required
            if search not in target_content:
                return {
                    "status": "error",
                    "message": "Search pattern not found in specified line range",
                }

        # Replace
        replacement_lines = replace.split("\n")
        if not replace.endswith("\n"):
            replacement_lines = [line + "\n" for line in replacement_lines[:-1]] + [
                replacement_lines[-1]
            ]
        else:
            replacement_lines = [line + "\n" for line in replacement_lines]

        new_lines = lines[: first_line - 1] + replacement_lines + lines[last_line:]

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return {
            "status": "success",
            "message": f"Replaced lines {first_line}-{last_line}",
            "old_line_count": last_line - first_line + 1,
            "new_line_count": len(replacement_lines),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# WEB TOOLS
# ============================================================================


def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Performs a web search and returns results.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        {
            "status": "success",
            "results": [
                {"title": "...", "url": "...", "snippet": "..."},
                ...
            ]
        }
    """
    try:
        # For now, return a placeholder
        # In production, integrate with Google Search API or similar
        return {
            "status": "success",
            "message": "Web search not fully implemented. Use fetch_web_page for specific URLs.",
            "results": [],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_web_page(url: str) -> Dict[str, Any]:
    """
    Fetches content from a web page.

    Args:
        url: URL to fetch

    Returns:
        {
            "status": "success",
            "url": "...",
            "title": "...",
            "content": "text content..."
        }
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Extract text
        title = soup.find("title").text if soup.find("title") else url

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        content = "\n".join(chunk for chunk in chunks if chunk)

        return {
            "status": "success",
            "url": url,
            "title": title,
            "content": content[:5000],  # Limit to 5000 chars
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# DESIGN TOOLS
# ============================================================================


def generate_design_inspiration(goal: str, context: str = "") -> Dict[str, Any]:
    """
    Generates design inspiration and guidelines for a UI project.

    Args:
        goal: High-level product/feature goal
        context: Optional design cues, brand adjectives, constraints

    Returns:
        {
            "status": "success",
            "design_brief": {
                "color_scheme": {...},
                "typography": {...},
                "layout": {...},
                "components": [...]
            }
        }
    """
    try:
        # Generate a simple design brief
        # In production, this could call an AI model
        design_brief = {
            "color_scheme": {
                "primary": "#4F46E5",
                "secondary": "#06B6D4",
                "background": "#FFFFFF",
                "text": "#1F2937",
            },
            "typography": {
                "heading_font": "Inter",
                "body_font": "System UI",
                "base_size": "16px",
            },
            "layout": {
                "max_width": "1200px",
                "spacing_unit": "8px",
                "grid_columns": 12,
            },
            "components": [
                "Header with navigation",
                "Hero section",
                "Feature cards",
                "Call-to-action",
                "Footer",
            ],
            "goal": goal,
            "context": context,
        }

        return {"status": "success", "design_brief": design_brief}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================


def manage_dependencies(action: str, package: str) -> Dict[str, Any]:
    """
    Manages project dependencies (add/remove npm packages).

    Args:
        action: "add" or "remove"
        package: Package name (e.g., "lodash@latest")

    Returns:
        {"status": "success", "message": "..."}
    """
    try:
        if action == "add":
            cmd = ["npm", "install", package]
        elif action == "remove":
            cmd = ["npm", "uninstall", package]
        else:
            return {"status": "error", "message": f"Invalid action: {action}"}

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Package {action}ed: {package}",
                "output": result.stdout,
            }
        else:
            return {"status": "error", "message": result.stderr}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# NEW WORKFLOW TOOLS (Analyze-Generate-Apply)
# ============================================================================


def analyze_code(file_path: str, change_request: str) -> Dict[str, Any]:
    """
    Analyze code to determine required changes.

    Args:
        file_path: File to analyze
        change_request: What user wants to change

    Returns:
        {"status": "success", "analysis": "...", "recommendation": "generate_code|edit_content"}
    """
    try:
        # Read the file
        file_result = read_file(file_path)
        if file_result["status"] != "success":
            return file_result

        content = file_result["content"]

        # Basic analysis
        is_code_change = any(
            keyword in change_request.lower()
            for keyword in [
                "component",
                "function",
                "logic",
                "feature",
                "add",
                "create",
                "implement",
            ]
        )
        is_content_change = any(
            keyword in change_request.lower()
            for keyword in ["text", "copy", "title", "heading", "content", "wording"]
        )

        recommendation = "generate_code" if is_code_change else "edit_content"

        analysis = {
            "file": file_path,
            "current_lines": file_result["total_lines"],
            "change_type": "code" if is_code_change else "content",
            "recommendation": recommendation,
            "request": change_request,
        }

        return {
            "status": "success",
            "analysis": analysis,
            "recommendation": recommendation,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def generate_code(
    file_path: str, description: str, existing_code: str = ""
) -> Dict[str, Any]:
    """
    Generate code for components/logic. Returns new code WITHOUT writing to disk.

    Args:
        file_path: Target file path
        description: What to generate
        existing_code: Current code (optional)

    Returns:
        {
            "status": "success",
            "file_path": "...",
            "generated_code": "...",
            "instructions": "Generated React component. Use apply_changes to save."
        }
    """
    try:
        # This is a placeholder - actual generation will be done by the AI model
        # The AI will use its knowledge to generate proper React/TypeScript code

        instructions = f"""Generated code for: {description}

File: {file_path}

Next step: Use apply_changes tool to write this code to the file.

Format your code using XML tags:
<file name="{file_path}">
// Your generated code here
</file>
"""

        return {
            "status": "success",
            "file_path": file_path,
            "description": description,
            "instructions": instructions,
            "note": "AI should generate the actual code and then use apply_changes to save it",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def edit_content(file_path: str, content_changes: str) -> Dict[str, Any]:
    """
    Edit UI content/text only. Returns changes WITHOUT writing to disk.

    Args:
        file_path: File to edit
        content_changes: What content to change

    Returns:
        {
            "status": "success",
            "file_path": "...",
            "changes": "...",
            "instructions": "Content changes prepared. Use apply_changes to save."
        }
    """
    try:
        # Read current file
        file_result = read_file(file_path)
        if file_result["status"] != "success":
            return file_result

        instructions = f"""Content changes for: {content_changes}

File: {file_path}

Next step: Use apply_changes tool to write the updated content.

Make only the text/content changes requested, preserving all code structure.
"""

        return {
            "status": "success",
            "file_path": file_path,
            "current_content": file_result["content"][:500] + "...",  # Preview
            "changes_requested": content_changes,
            "instructions": instructions,
            "note": "AI should make content changes and use apply_changes to save",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def apply_changes(file_path: str, new_content: str) -> Dict[str, Any]:
    """
    Write changes to file. Use after generate_code or edit_content.

    Args:
        file_path: File to update
        new_content: Complete new file content

    Returns:
        {"status": "success", "message": "File updated: ..."}
    """
    try:
        # Use write_file to save
        result = write_file(file_path, new_content)

        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"✅ Applied changes to {file_path}",
                "file_path": file_path,
                "lines_written": result["lines_written"],
            }
        else:
            return result

    except Exception as e:
        return {"status": "error", "message": str(e)}


def apply_multiple_changes(changes: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Update multiple files in one go.

    Args:
        changes: List of dicts, each containing 'file_path' and 'new_content'
                 [
                    {"file_path": "components/Navbar.tsx", "new_content": "..."},
                    {"file_path": "app/layout.tsx", "new_content": "..."}
                 ]

    Returns:
        Summary of applied changes
    """
    results = []
    success_count = 0
    fail_count = 0

    for change in changes:
        file_path = change.get("file_path")
        new_content = change.get("new_content")

        if not file_path or not new_content:
            results.append(
                {
                    "file_path": file_path or "unknown",
                    "status": "error",
                    "message": "Missing file_path or new_content",
                }
            )
            fail_count += 1
            continue

        result = write_file(file_path, new_content)
        results.append(
            {
                "file_path": file_path,
                "status": result["status"],
                "message": result["message"],
            }
        )

        if result["status"] == "success":
            success_count += 1
        else:
            fail_count += 1

    return {
        "status": "success" if success_count > 0 else "error",
        "message": f"Updated {success_count} files, failed {fail_count} files",
        "results": results,
        "total_files": len(changes),
    }


def replace_code_segment(
    file_path: str, search_pattern: str, replacement_code: str, use_regex: bool = True
) -> Dict[str, Any]:
    """
    Find and replace a specific code segment using regex or exact match.

    Args:
        file_path: File to modify
        search_pattern: Regex pattern or exact string to find
        replacement_code: New code to replace with
        use_regex: Whether to treat search_pattern as regex (default True)

    Returns:
        {"status": "success", "message": "Replaced X occurrences", "matches": X}
    """
    try:
        # Read file
        file_result = read_file(file_path)
        if file_result["status"] != "success":
            return file_result

        content = file_result["content"]

        # Perform replacement
        if use_regex:
            # Use regex
            pattern = re.compile(search_pattern, re.MULTILINE | re.DOTALL)
            new_content, count = pattern.subn(replacement_code, content)
        else:
            # Exact string match
            if search_pattern in content:
                new_content = content.replace(search_pattern, replacement_code)
                count = 1
            else:
                return {
                    "status": "error",
                    "message": f"Pattern not found in {file_path}",
                }

        if count == 0:
            return {
                "status": "error",
                "message": f"Pattern '{search_pattern}' not found in {file_path}",
            }

        # Write back
        write_result = write_file(file_path, new_content)

        if write_result["status"] == "success":
            return {
                "status": "success",
                "message": f"✅ Replaced {count} occurrence(s) in {file_path}",
                "file_path": file_path,
                "matches": count,
                "lines_written": write_result["lines_written"],
            }
        else:
            return write_result

    except re.error as e:
        return {"status": "error", "message": f"Invalid regex pattern: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
