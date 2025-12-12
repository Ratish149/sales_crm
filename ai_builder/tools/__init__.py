"""
AI Builder Tools Package

This package contains all the tools that the AI agent can use
to interact with the project files, web, and generate content.
"""

from .tools import (
    # New workflow tools
    analyze_code,
    apply_changes,
    apply_multiple_changes,
    delete_file,
    edit_content,
    fetch_web_page,
    generate_code,
    generate_design_inspiration,
    list_files,
    manage_dependencies,
    read_file,
    replace_code_segment,
    replace_in_file,
    search_files,
    web_search,
    write_file,
)

__all__ = [
    # File operations
    "list_files",
    "read_file",
    "search_files",
    "write_file",
    "delete_file",
    "replace_in_file",
    # Web tools
    "web_search",
    "fetch_web_page",
    # Design tools
    "generate_design_inspiration",
    # Dependency management
    "manage_dependencies",
    # New workflow tools
    "analyze_code",
    "generate_code",
    "edit_content",
    "apply_changes",
    "replace_code_segment",
    "apply_multiple_changes",
]
