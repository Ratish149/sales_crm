import json
import re
import time
from typing import Any, Dict, List

from asgiref.sync import async_to_sync

from .agents import GeminiAgent
from .scanner import ProjectScanner


class WebBuilderOrchestrator:
    def __init__(self, project_root: str, tenant_name: str, api_key: str = None):
        self.scanner = ProjectScanner(project_root)
        self.project_root = project_root
        self.tenant_name = tenant_name

        # WebSocket Group Name (optional)
        self.group_name = f"workspace_{tenant_name}"

        # Try to get channel layer, but don't fail if not configured
        try:
            from channels.layers import get_channel_layer

            self.channel_layer = get_channel_layer()
        except Exception as e:
            print(f"⚠️  Channels not configured, WebSocket updates disabled: {e}")
            self.channel_layer = None

        # Initialize agent
        self.agent = GeminiAgent(api_key=api_key)

    def _broadcast_status(self, message: str, status_type: str = "info"):
        """Sends a status update to the WebSocket group."""
        print(f"📡 {message}")

        # Skip if channels not configured
        if not self.channel_layer:
            return

        try:
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "ai_notification_event",
                    "message": message,
                    "status_type": status_type,
                    "timestamp": time.time(),
                },
            )
        except Exception as e:
            print(f"⚠️ Failed to broadcast status: {e}")

    def build(self, user_prompt: str, auto_apply: bool = True) -> Dict[str, Any]:
        """
        Orchestrates the build process using local file search (fast).

        Args:
            user_prompt: The user's request for what to build/modify
            auto_apply: If True, automatically writes generated code to disk
        """
        print(f"🚀 Starting build for: {user_prompt}")
        self._broadcast_status(f"🚀 AI Agent Started: {user_prompt}", "info")

        # --- STEP 1: GATHER CONTEXT LOCALLY ---
        print("📂 Scanning project files locally...")
        self._broadcast_status("📂 Scanning project structure...", "loading")

        readme_content = self.scanner.get_readme_content()
        all_files = self.scanner.list_files(max_depth=5)
        resources_summary = self.scanner.scan_project_resources()

        # Create a file tree summary
        file_tree = "\n".join([f"  - {f}" for f in all_files[:50]])  # Limit to first 50
        if len(all_files) > 50:
            file_tree += f"\n  ... and {len(all_files) - 50} more files"

        print(f"✅ Found {len(all_files)} files")
        self._broadcast_status(f"✅ Scanned {len(all_files)} files", "success")

        # --- STEP 2: ANALYSIS (Identify Files Locally) ---
        print("🧠 Analyzing requirements...")
        self._broadcast_status("🧠 Analyzing which files to modify...", "loading")

        analysis_prompt = f"""
USER REQUEST: "{user_prompt}"

PROJECT CONTEXT:
README:
{readme_content[:2000]}

PROJECT FILES:
{file_tree}

{resources_summary}

TASK:
Based on the user request, identify which files need to be READ or MODIFIED.

CRITICAL INSTRUCTIONS:
1. **TRACE IMPORTS**: If modifying UI (e.g., "Hero Section"), find the actual component file
2. **Deep Search**: Look in /src/components, /src/app/_components
3. **Avoid Duplication**: Don't create new files if components exist
4. Always include 'package.json'

OUTPUT FORMAT:
Return ONLY a JSON array of file paths.
Example: ["src/app/page.tsx", "src/components/HeroSection.tsx", "package.json"]
"""

        response = self.agent.generate_content(prompt=analysis_prompt)

        # Save usage log for analysis
        self._save_usage_log(
            prompt=analysis_prompt,
            response=response,
            action_type="analysis",
            model_name=self.agent.model_name,
        )

        # Parse the response
        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]

        target_files = ["package.json"]
        try:
            target_files = json.loads(cleaned_response)
            print(f"🎯 Files identified: {target_files}")
            self._broadcast_status(f"🎯 Identified {len(target_files)} files", "info")
        except Exception as e:
            print(f"⚠️ Failed to parse analysis JSON: {e}")
            self._broadcast_status("⚠️ Using default file selection", "warning")

        # --- STEP 3: READ FILE CONTENTS ---
        print("📖 Reading file contents...")
        file_contents = self.scanner.read_files(target_files)

        formatted_contents = ""
        for path, content in file_contents.items():
            formatted_contents += f"\n## FILE: {path}\n```\n{content}\n```\n"

        # --- STEP 4: GENERATION ---
        print("🎨 Generating code...")
        self._broadcast_status("🎨 Generating code changes...", "loading")

        generation_prompt = f"""
You are a World-Class Full-Stack Next.js 14 Developer and Senior UI Designer.

USER REQUEST: "{user_prompt}"

CONTEXT FILES:
{formatted_contents}

{resources_summary}

TASK:
Generate the necessary code changes.
- Follow Next.js 14 best practices (App Router, Server Components)
- Use existing components
- Provide FULL file content for safety

CRITICAL RULES FOR DATA:
1. **USE EXISTING HOOKS**: Use hooks from 'Data Fetching Hooks'. Do NOT mock data
2. **USE EXISTING TYPES**: Use types from 'Project Types'. Ensure strict typing
3. **NO NEW SERVICE CALLS**: Use abstracted hooks or 'API Services'
4. **NEVER HARDCODE DATA**: Wire up dynamic data using provided resources

CRITICAL RULES FOR IMAGES:
1. **NO HARDCODED PATHS**: If you use a static image (e.g. placeholder, hero bg), DO NOT hardcode the path in JSX.
2. **EXTRACT TO JSON**: Generate/Update `src/content/images.json` with a semantic key.
   Example `src/content/images.json`:
   ```json
   {{
     "hero_bg": "/images/hero-bg.jpg",
     "feature_icon_1": "/images/icon-1.png"
   }}
   ```
3. **IMPORT & USE**: Import the JSON and use the key:
   `import images from "@/content/images.json";`
   `<Image src={{images.hero_bg}} ... />`
4. If `src/content/images.json` does not exist, CREATE IT.

OUTPUT FORMAT:
## FILE: path/to/file.ext
```language
content
```
"""

        generation_response = self.agent.generate_content(generation_prompt)
        print("✅ Generation complete.")
        self._broadcast_status("✅ Code generation complete", "success")

        # Save usage log for generation
        self._save_usage_log(
            prompt=generation_prompt,
            response=generation_response,
            action_type="generation",
            model_name=self.agent.model_name,
        )

        modifications = self._parse_generation_response(generation_response.text)

        self._broadcast_status(
            f"✅ Generated changes for {len(modifications)} files", "success"
        )

        # Apply modifications if auto_apply is enabled
        apply_results = None
        if auto_apply:
            apply_results = self.apply_modifications(modifications, auto_apply=True)

        return {
            "status": "success",
            "analysis": target_files,
            "modifications": modifications,
            "raw_response": generation_response.text,
            "apply_results": apply_results,
        }

    def _save_usage_log(
        self, prompt: str, response: Any, action_type: str, model_name: str
    ):
        """Saves usage statistics to the database."""
        try:
            from .models import AIUsageLog

            # Extract usage directly from response object
            usage = {
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0,
            }

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage["prompt_token_count"] = (
                    response.usage_metadata.prompt_token_count or 0
                )
                usage["candidates_token_count"] = (
                    response.usage_metadata.candidates_token_count or 0
                )
                usage["total_token_count"] = (
                    response.usage_metadata.total_token_count or 0
                )

            AIUsageLog.objects.create(
                tenant_name=self.tenant_name,
                user_prompt=prompt[:5000],  # Truncate if too long
                action_type=action_type,
                model_name=model_name,
                input_tokens=usage.get("prompt_token_count", 0),
                output_tokens=usage.get("candidates_token_count", 0),
                total_tokens=usage.get("total_token_count", 0),
            )
            print(
                f"📊 Saved usage log for {action_type}: {usage.get('total_token_count', 0)} tokens"
            )
        except Exception as e:
            print(f"⚠️ Failed to save usage log: {e}")

    def _parse_generation_response(self, response: str) -> List[Dict[str, str]]:
        """Parses the LLM output into a list of file modifications."""
        segments = response.split("## FILE:")
        modifications = []

        for segment in segments[1:]:
            try:
                lines = segment.strip().split("\n", 1)
                if not lines:
                    continue
                file_path = lines[0].strip()

                code_segment = lines[1] if len(lines) > 1 else ""

                # regex to find code block
                start_match = re.search(r"```\w*\n", code_segment)
                if start_match:
                    start_idx = start_match.end()
                    end_idx = code_segment.rfind("```")
                    if end_idx != -1:
                        code_content = code_segment[start_idx:end_idx]
                        modifications.append(
                            {"path": file_path, "content": code_content}
                        )
            except Exception as e:
                print(f"⚠️ Error parsing segment: {e}")
                continue

        return modifications

    def apply_modifications(
        self, modifications: List[Dict[str, str]], auto_apply: bool = True
    ) -> Dict[str, Any]:
        """
        Writes the generated code modifications to disk.

        Args:
            modifications: List of dicts with 'path' and 'content' keys
            auto_apply: If True, automatically writes files. If False, returns preview only.

        Returns:
            Dict with status and details of files written
        """
        import os

        results = {
            "status": "success",
            "files_written": [],
            "files_skipped": [],
            "errors": [],
        }

        if not auto_apply:
            results["status"] = "preview_only"
            results["message"] = "Auto-apply is disabled. No files were written."
            return results

        print(f"\n📝 Applying {len(modifications)} file modifications...")
        self._broadcast_status(
            f"📝 Writing {len(modifications)} files to disk...", "loading"
        )

        for mod in modifications:
            file_path = mod["path"]
            content = mod["content"]

            # Construct full path
            full_path = os.path.join(self.project_root, file_path)

            try:
                # Create directory if it doesn't exist
                directory = os.path.dirname(full_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    print(f"   📁 Created directory: {directory}")

                # Write file
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"   ✅ Written: {file_path}")
                results["files_written"].append(file_path)

            except Exception as e:
                error_msg = f"Failed to write {file_path}: {str(e)}"
                print(f"   ❌ {error_msg}")
                results["errors"].append(error_msg)

        # Broadcast completion
        if results["files_written"]:
            self._broadcast_status(
                f"✅ Successfully wrote {len(results['files_written'])} files",
                "success",
            )

        if results["errors"]:
            results["status"] = (
                "partial_success" if results["files_written"] else "failed"
            )
            self._broadcast_status(
                f"⚠️ {len(results['errors'])} files failed to write", "warning"
            )

        return results
