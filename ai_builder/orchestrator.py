import os
from typing import Any, Dict

from dotenv import load_dotenv

from .agent import GeminiAgent
from .structure_scanner import get_project_structure_summary
from .tools import (
    apply_changes,
    apply_multiple_changes,
    delete_file,
    fetch_web_page,
    generate_design_inspiration,
    list_files,
    manage_dependencies,
    read_file,
    replace_in_file,
    search_files,
    web_search,
    write_file,
)

load_dotenv()


# Map tool names to functions (simplified for main flow, but keeping others available)
TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "apply_multiple_changes": apply_multiple_changes,
    "apply_changes": apply_changes,
    "write_file": write_file,
    "delete_file": delete_file,
    "search_files": search_files,
    "replace_in_file": replace_in_file,
    "web_search": web_search,
    "fetch_web_page": fetch_web_page,
    "generate_design_inspiration": generate_design_inspiration,
    "manage_dependencies": manage_dependencies,
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name."""
    if name not in TOOL_FUNCTIONS:
        return {"status": "error", "message": f"Unknown tool: {name}"}

    try:
        func = TOOL_FUNCTIONS[name]
        result = func(**arguments)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Tool execution failed: {str(e)}"}


def orchestrate_agent(
    user_prompt: str, project_root: str, max_iterations: int = 5
) -> Dict[str, Any]:
    """
    Orchestrates the AI agent in a SINGLE-SHOT workflow using MARKDOWN PARSING.
    """
    try:
        if not os.path.exists(project_root):
            return {
                "status": "error",
                "message": f"Project root not found: {project_root}",
            }

        original_cwd = os.getcwd()
        os.chdir(project_root)

        # 1. SCAN PROJECT STRUCTURE
        print("\n" + "=" * 80)
        print("🔍 SCANNING PROJECT STRUCTURE")
        print("=" * 80)
        try:
            project_summary = get_project_structure_summary(project_root)
            print(f"✅ Project scanned. Root: {project_root}")
        except Exception as e:
            print(f"⚠️ Structure scan failed: {e}")
            project_summary = f"Project Root: {project_root}"

        # 2. CONSTRUCT SYSTEM PROMPT (The "Brain")
        system_prompt = f"""You are an expert Senior Full-Stack React/Vite Developer and UI/UX Designer.
You build stunning, modern web applications that wow users

**YOUR GOAL**:
Receive a user prompt -> Analyze it -> Generate ALL necessary file changes -> Output them in a specific MARKDOWN format.

**CRITICAL: FILE TARGETING AND PATH ACCURACY RULES**:
1.  **SPECIFICITY IS KING**: NEVER modify "all files with name X". Only modify the *specific* file relevant to the request.
2.  **AMBIGUITY RESOLUTION**: If the user asks to change "the page" or "page.tsx", they ALMOST ALWAYS mean the root/main page (`app/page.tsx`).
3.  **DO NOT TOUCH**: Do not modify `app/about/page.tsx`, `app/contact/page.tsx` etc. unless the user explicitly mentions "about page" or "contact page".
4.  **CONTEXT AWARENESS**: Look at the file path. Does the change make sense for this specific route?
5.  **PATH ACCURACY**: Always Use the **ACTUAL** file path from the project structure. Do not invent paths.

**VISUAL & CODE STANDARDS**:
1. **Aesthetic**: Clean, modern, premium. Use ample whitespace, consistent spacing, and harmonious color palettes.
2. **Styling**: ALWAYS use **Tailwind CSS**. Use gradients, glassmorphism, and shadow effects to make UI pop.
3. **Icons**: Use `lucide-react` for icons.
4. **Components**: Create small, reusable functional components with named exports.
5. **Responsiveness**: All UIs must be fully responsive (mobile-first).

**PROJECT CONTEXT**:
{project_summary}

**USER REQUEST**:
"{user_prompt}"

**YOUR MISSION**:
1. **ANALYZE**: Understand what the user wants.
2. **PLAN**: Determine exactly which files need to be created or modified.
3. **GENERATE**: Write the COMPLETE, PRODUCTION-READY code for EVERY file.

**CRITICAL OUTPUT FORMAT**:
You must output the code using the following format for EACH file.
**DO NOT** list all files at the beginning.
**STRICTLY FOLLOW THIS PATTERN**:
1. Write "## FILE: path/to/filename.ext"
2. IMMEDIATELY write the code block (```language ... ```)
3. Move to the next file.

## FILE: path/to/filename.ext
```language
... complete code ...
```

**TO DELETE A FILE**:
1. Write "## FILE: path/to/filename.ext"
2. In the code block, write EXACTLY `<<DELETE>>`
Example:
## FILE: path/to/delete.txt
```
<<DELETE>>
```

**DO NOT** Use tool calls. Just output the text.
**ONE SHOT**: Generate all files in your first response.

**MAGIC INSTRUCTION**:
Over-deliver on design. seamless, polished, and beautiful.
"""

        # 3. INITIALIZE AGENT
        api_key = os.getenv("GOOGLE_API_KEY")

        print("API Key: ", api_key)
        if not api_key:
            os.chdir(original_cwd)
            return {
                "status": "error",
                "message": "GOOGLE_API_KEY not found. Please check .env file.",
            }

        # Initialize WITHOUT tools for the main generation phase to force text output
        agent = GeminiAgent(use_tools=False)

        # 4. EXECUTE (Expectation: 1 turn)
        print("\n" + "=" * 80)
        print("⚡ EXECUTING AI WORKFLOW (Text -> Code)")
        print("=" * 80)

        response = agent.send_message(system_prompt)

        conversation_log = []
        files_modified = []

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Turn {iteration}")

            conversation_log.append({"iteration": iteration, "response": response})

            # PARSE RESPONSE FOR FILES
            if response["type"] == "final_answer":
                content = str(response["content"])
                print("🧠 AI Response received. Parsing files...")

                # Robust parsing strategy: Split by "## FILE:" marker
                segments = content.split("## FILE:")

                found_files = False

                for i in range(1, len(segments)):
                    segment = segments[i]
                    # The first line is the filename
                    lines = segment.strip().split("\n", 1)
                    if not lines:
                        continue

                    file_path = lines[0].strip()
                    if not file_path:
                        continue

                    print(f"🔍 Analyzing segment for: {file_path}")

                    # DUMB PARSER: Find matched backticks manually
                    start_pattern = "```"
                    end_pattern = "```"

                    start_idx = segment.find(start_pattern)
                    if start_idx != -1:
                        # Find end of the opening tick line (to skip language identifier)
                        newline_idx = segment.find("\n", start_idx)
                        if newline_idx != -1:
                            content_start = newline_idx + 1

                            # Find closing ticks AFTER content start
                            end_idx = segment.find(end_pattern, content_start)

                            if end_idx != -1:
                                found_files = True
                                new_content = segment[content_start:end_idx]

                                print(f"📦 Found file: {file_path}")

                                # Check for delete marker
                                if new_content.strip() == "<<DELETE>>":
                                    print(f"🗑️ Deleting file: {file_path}")
                                    result = delete_file(file_path)
                                    if result["status"] == "success":
                                        files_modified.append(file_path + " (DELETED)")
                                        print(f"✅ Deleted: {file_path}")
                                    else:
                                        print(
                                            f"❌ Failed to delete {file_path}: {result['message']}"
                                        )
                                else:
                                    # Apply changes
                                    result = write_file(file_path, new_content)
                                    if result["status"] == "success":
                                        files_modified.append(file_path)
                                        print(f"✅ Modified: {file_path}")
                                    else:
                                        print(
                                            f"❌ Failed to modify {file_path}: {result['message']}"
                                        )
                            else:
                                print(f"⚠️ Closing backticks not found for {file_path}")
                        else:
                            print(
                                f"⚠️ Newline after opening backticks not found for {file_path}"
                            )
                    else:
                        print(f"⚠️ No code block start (```) found for {file_path}")
                        print(f"Segment preview: {repr(segment[:100])}")

                if found_files:
                    print(
                        f"\n✅ Processing complete. Modified {len(files_modified)} files."
                    )
                    break
                else:
                    print("⚠️ No file blocks found in AI response.")
                    print(f"Response preview: {content[:200]}...")

            elif response["type"] == "tool_calls":
                # With use_tools=False, this should NOT happen.
                print("⚠️ Unexpected tool call in text-only mode.")
                tool_results = []
                for tool_call in response["tool_calls"]:
                    name = tool_call["name"]
                    args = tool_call["arguments"]

                    print(f"🛠️ CALLING TOOL: {name.upper()}")
                    result = execute_tool(name, args)
                    tool_results.append({"name": name, "result": result})

                response = agent.send_tool_results(tool_results)
                continue

            elif response["type"] == "error":
                print(f"❌ Error: {response['content']}")
                break

            break

        os.chdir(original_cwd)

        print("\n" + "=" * 80)
        print(f"🎉 WORKFLOW COMPLETE. Modified {len(files_modified)} files.")
        print("=" * 80 + "\n")

        return {
            "status": "success",
            "files_modified": list(set(files_modified)),
            "conversation_log": conversation_log,
            "iterations": iteration,
        }

    except Exception as e:
        os.chdir(original_cwd)
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}
