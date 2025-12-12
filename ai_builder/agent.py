"""
Gemini Agent Module

This module provides the Gemini AI client integration and tool schema definitions
for the agentic workflow.
"""

import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

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
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        genai.configure(api_key=self.api_key)

        # Initialize model with tools if enabled
        tools = TOOL_SCHEMAS if use_tools else None

        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=tools,
        )

        self.conversation_history = []

        # Token usage tracking
        self.token_usage = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
        }

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
        try:
            # Truncate history to save tokens
            self._truncate_history()

            # Create chat
            chat = self.model.start_chat(history=self.conversation_history)

            # Send message
            response = chat.send_message(message)
            self._update_token_usage(response)

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
                        {"role": "model", "parts": response.candidates[0].content.parts}
                    )

                    return {"type": "tool_calls", "tool_calls": tool_calls}

                # Regular text response
                elif hasattr(part, "text"):
                    text = part.text

                    self.conversation_history.append({"role": "model", "parts": [text]})

                    return {"type": "final_answer", "content": text}

            return {"type": "error", "content": "No valid response from model"}

        except Exception as e:
            return {"type": "error", "content": str(e)}

    def send_tool_results(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send tool execution results back to the agent.

        Args:
            tool_results: List of {name, result} dicts

        Returns:
            Next response from agent
        """
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

            # Add to history
            self.conversation_history.append(
                {"role": "function", "parts": function_responses}
            )

            # Truncate history to save tokens
            self._truncate_history()

            # Continue conversation by generating content from history
            # We don't use chat.send_message("") because that adds an empty user message
            response = self.model.generate_content(self.conversation_history)
            self._update_token_usage(response)

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
                        {"role": "model", "parts": response.candidates[0].content.parts}
                    )

                    return {"type": "tool_calls", "tool_calls": tool_calls}

                elif hasattr(part, "text"):
                    text = part.text

                    self.conversation_history.append({"role": "model", "parts": [text]})

                    return {"type": "final_answer", "content": text}

            return {"type": "error", "content": "No valid response from model"}

        except Exception as e:
            return {"type": "error", "content": str(e)}
