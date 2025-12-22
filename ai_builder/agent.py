"""
Gemini Agent Module

This module provides the Gemini AI client integration and tool schema definitions
for the agentic workflow.
"""

import os
import random
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Import APIKey model
# We use a try-except block or delayed import to avoid issues if apps aren't ready
try:
    from ai_builder.models import APIKey
except ImportError:
    APIKey = None

load_dotenv()

# ============================================================================
# TOOL SCHEMAS FOR GEMINI (MINIMAL - saves tokens)
# ============================================================================

TOOL_SCHEMAS = [
    {
        "name": "list_files",
        "description": "List files in directory",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Path to list"},
                "glob_pattern": {"type": "STRING", "description": "Filter (*.tsx)"},
            },
        },
    },
    {
        "name": "read_file",
        "description": "Read file content",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "File to read"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "apply_changes",
        "description": "Write code to file (creates or overwrites)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "File to update"},
                "new_content": {
                    "type": "STRING",
                    "description": "Complete file content",
                },
            },
            "required": ["file_path", "new_content"],
        },
    },
    {
        "name": "apply_multiple_changes",
        "description": "Write code to multiple files at once. Use this for all multi-file operations.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "changes": {
                    "type": "ARRAY",
                    "description": "List of file updates",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "file_path": {
                                "type": "STRING",
                                "description": "Target file path",
                            },
                            "new_content": {
                                "type": "STRING",
                                "description": "Complete, production-ready file content",
                            },
                        },
                        "required": ["file_path", "new_content"],
                    },
                }
            },
            "required": ["changes"],
        },
    },
    {
        "name": "replace_code_segment",
        "description": "Replace code using regex",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "File to modify"},
                "search_pattern": {"type": "STRING", "description": "Regex pattern"},
                "replacement_code": {"type": "STRING", "description": "New code"},
            },
            "required": ["file_path", "search_pattern", "replacement_code"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "File to delete"},
            },
            "required": ["file_path"],
        },
    },
]


# ============================================================================
# GEMINI CLIENT
# ============================================================================


class GeminiAgent:
    """Gemini AI Agent with tool calling capabilities."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        use_tools: bool = True,
    ):
        """
        Initialize the Gemini agent.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model_name: Model to use
            use_tools: Whether to enable tool calling (default True)
        """
        self.model_name = model_name
        self.use_tools = use_tools
        self.tools = TOOL_SCHEMAS if use_tools else None
        self.conversation_history = []
        self.token_usage = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
        }

        # Initialize API Key
        self.api_key = api_key
        self._initialize_api_key()

    def _initialize_api_key(self):
        """Pick an available API key and configure genai."""
        if self.api_key:
            # If explicit key provided, use it
            genai.configure(api_key=self.api_key)
            self._update_model()
            return

        # Try to get from DB
        db_key = self._get_db_key()
        if db_key:
            print(f"🔑 Using API Key from DB: {db_key[:10]}...")
            self.api_key = db_key
            genai.configure(api_key=self.api_key)
            self._update_model()
            return

        # Fallback to env var
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            print("🔑 Using API Key from Environment")
            self.api_key = env_key
            genai.configure(api_key=self.api_key)
            self._update_model()
            return

        raise ValueError("No valid Google API Key found (DB or Environment)")

    def _get_db_key(self, exclude_key: str = None) -> Optional[str]:
        """Fetch an API Key from the database. Prioritizes active keys."""
        if not APIKey:
            return None

        try:
            # 1. Try to find an ACTIVE key first
            active_keys = APIKey.objects.filter(is_active=True)
            if exclude_key:
                active_keys = active_keys.exclude(key=exclude_key)

            if active_keys.exists():
                key_obj = active_keys.first()  # Pick the first active one
                key_obj.usage_count += 1
                key_obj.save()
                return key_obj.key

            # 2. If no active key (or all active were excluded/failed), pick any INACTIVE key
            inactive_keys = APIKey.objects.filter(is_active=False)
            if exclude_key:
                inactive_keys = inactive_keys.exclude(key=exclude_key)

            if inactive_keys.exists():
                key_obj = random.choice(
                    list(inactive_keys)
                )  # Randomly pick a trial key
                key_obj.usage_count += 1
                key_obj.save()
                return key_obj.key

        except Exception as e:
            print(f"⚠️ Error fetching key from DB: {e}")
            return None

        return None

    def _mark_key_success(self, key: str):
        """Mark this key as THE active key, and others as inactive."""
        if not APIKey or not key:
            return

        try:
            # Check if it's a DB key
            key_obj = APIKey.objects.filter(key=key).first()
            if key_obj:
                print(f"✅ Key {key[:10]}... is working. Setting as PRIMARY ACTIVE.")
                # Set this one to True
                key_obj.is_active = True
                key_obj.save()

                # Set all OTHERS to False (Strict single active key policy)
                APIKey.objects.exclude(pk=key_obj.pk).update(is_active=False)
        except Exception as e:
            print(f"⚠️ Error updating key status: {e}")

    def _mark_key_failure(self, key: str):
        """Mark this key as inactive."""
        if not APIKey or not key:
            return

        try:
            key_obj = APIKey.objects.filter(key=key).first()
            if key_obj:
                print(f"❌ Key {key[:10]}... failed. Marking INACTIVE.")
                key_obj.is_active = False
                key_obj.save()
        except Exception as e:
            print(f"⚠️ Error marking key inactive: {e}")

    def _rotate_key(self) -> bool:
        """Switch to a different API Key. Returns True if successful."""
        print("🔄 Rotating API Key...")
        current_key = self.api_key

        # Mark current as failed
        self._mark_key_failure(current_key)

        # Try to get a different key from DB
        new_key = self._get_db_key(exclude_key=current_key)

        if new_key:
            print(f"✅ Switched to new key: {new_key[:10]}...")
            self.api_key = new_key
            genai.configure(api_key=self.api_key)
            self._update_model()
            return True

        # If we were using DB key and failed to find another, check env var
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key and env_key != current_key:
            print("✅ Switched to Environment Key")
            self.api_key = env_key
            genai.configure(api_key=self.api_key)
            self._update_model()
            return True

        print("❌ No other keys available to rotate to.")
        return False

    def _update_model(self):
        """Re-initialize the generative model with current config."""
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools,
        )

    def _update_token_usage(self, response):
        """Update token usage statistics from response."""
        if hasattr(response, "usage_metadata"):
            self.token_usage["prompt_tokens"] += (
                response.usage_metadata.prompt_token_count
            )
            self.token_usage["candidates_tokens"] += (
                response.usage_metadata.candidates_token_count
            )
            self.token_usage["total_tokens"] += (
                response.usage_metadata.total_token_count
            )

    def _truncate_history(self, max_messages: int = 12):
        """Truncate conversation history to save tokens.

        Keeps the first message (system prompt) and the last N messages.
        This prevents token usage from growing exponentially.

        Args:
            max_messages: Maximum number of messages to keep (default 12 = ~6 turns)
        """
        if len(self.conversation_history) <= max_messages + 1:
            return  # No need to truncate

        # Keep first message (system) + last N messages
        first_message = self.conversation_history[0]
        recent_messages = self.conversation_history[-(max_messages):]

        self.conversation_history = [first_message] + recent_messages

    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Send a message to the agent and get response.

        Args:
            message: User message

        Returns:
            {
                "type": "tool_calls" | "final_answer",
                "content": {...} | "text response",
                "tool_calls": [...] if type is tool_calls
            }
        """
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                # Truncate history to save tokens
                self._truncate_history()

                # Create chat
                chat = self.model.start_chat(history=self.conversation_history)

                # Send message
                response = chat.send_message(message)
                self._update_token_usage(response)

                # Mark Success
                self._mark_key_success(self.api_key)

                # Update history
                self.conversation_history.append({"role": "user", "parts": [message]})

                # Parse response
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]

                    # Check if it's a function call
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls = []
                        for fc_part in response.candidates[0].content.parts:
                            if hasattr(fc_part, "function_call"):
                                tool_calls.append(
                                    {
                                        "name": fc_part.function_call.name,
                                        "arguments": dict(fc_part.function_call.args),
                                    }
                                )

                        self.conversation_history.append(
                            {
                                "role": "model",
                                "parts": response.candidates[0].content.parts,
                            }
                        )

                        return {"type": "tool_calls", "tool_calls": tool_calls}

                    # Regular text response
                    elif hasattr(part, "text"):
                        text = part.text

                        self.conversation_history.append(
                            {"role": "model", "parts": [text]}
                        )

                        return {"type": "final_answer", "content": text}

                return {"type": "error", "content": "No valid response from model"}

            except Exception as e:
                print(f"⚠️ Error in send_message (Attempt {attempt + 1}): {e}")
                attempt += 1

                # If we have retries left, try rotating key
                if attempt < max_retries:
                    if self._rotate_key():
                        print("🔁 Retrying with new key...")
                        continue

                return {"type": "error", "content": str(e)}

    def send_tool_results(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send tool execution results back to the agent.

        Args:
            tool_results: List of {name, result} dicts

        Returns:
            Next response from agent
        """
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                # Format tool results for Gemini
                function_responses = []
                for tr in tool_results:
                    function_responses.append(
                        {
                            "function_response": {
                                "name": tr["name"],
                                "response": tr["result"],
                            },
                        }
                    )

                # Add to history (only once!)
                # Note: We need to be careful not to add duplicate history on retry
                # But since we're generating content based on history, if we fail to generate,
                # the history is not yet "consumed" effectively.
                # Actually, we should probably add the function response to history BEFORE the loop
                # checking if it's already there?
                # Simplification: We assume the error happens during generate_content.
                # So we add to history first.

                # Check if the last message is already the function response we are trying to add
                # to avoid duplication on retry loop if we structured this differently.
                # But here, we construct the list and append.

                # CRITICAL: We should only append if this is the first attempt, OR clean up on failure.
                # Easier: Construct the new history locally for the call? No, start_chat uses history.
                # generate_content uses history list.

                if attempt == 0:
                    self.conversation_history.append(
                        {"role": "function", "parts": function_responses}
                    )

                # Truncate history to save tokens
                self._truncate_history()

                # Continue conversation by generating content from history
                response = self.model.generate_content(self.conversation_history)
                self._update_token_usage(response)

                # Mark Success
                self._mark_key_success(self.api_key)

                # Parse response (same logic as send_message)
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]

                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls = []
                        for fc_part in response.candidates[0].content.parts:
                            if hasattr(fc_part, "function_call"):
                                tool_calls.append(
                                    {
                                        "name": fc_part.function_call.name,
                                        "arguments": dict(fc_part.function_call.args),
                                    }
                                )

                        self.conversation_history.append(
                            {
                                "role": "model",
                                "parts": response.candidates[0].content.parts,
                            }
                        )

                        return {"type": "tool_calls", "tool_calls": tool_calls}

                    elif hasattr(part, "text"):
                        text = part.text

                        self.conversation_history.append(
                            {"role": "model", "parts": [text]}
                        )

                        return {"type": "final_answer", "content": text}

                return {"type": "error", "content": "No valid response from model"}

            except Exception as e:
                print(f"⚠️ Error in send_tool_results (Attempt {attempt + 1}): {e}")
                attempt += 1

                if attempt < max_retries:
                    if self._rotate_key():
                        print("🔁 Retrying with new key...")
                        # We don't need to re-append function response to history as it's already there from attempt 0
                        continue

                return {"type": "error", "content": str(e)}
