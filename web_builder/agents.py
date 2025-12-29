import os
import random
import time
from typing import Any, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Try to import APIKey model
try:
    from ai_builder.models import APIKey
except ImportError:
    APIKey = None

load_dotenv()


class GeminiAgent:
    """Gemini AI Agent using the google.genai SDK with File Search support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        system_instruction: Optional[str] = None,
    ):
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.api_key = api_key
        self._initialize_api_key()
        self.client = genai.Client(api_key=self.api_key)

    def _initialize_api_key(self):
        """Pick an available API key."""
        if self.api_key:
            return

        db_key = self._get_db_key()
        if db_key:
            self.api_key = db_key
            print("Using Google API Key from DB", db_key)
            return

        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            self.api_key = env_key
            print("Using Google API Key from Environment", env_key)
            return

        print("No valid Google API Key found (DB or Environment)")

        raise ValueError("No valid Google API Key found (DB or Environment)")

    def _get_db_key(self, exclude_key: str = None) -> Optional[str]:
        if not APIKey:
            return None
        try:
            active_keys = APIKey.objects.filter(is_active=True)
            if exclude_key:
                active_keys = active_keys.exclude(key=exclude_key)
            if active_keys.exists():
                return active_keys.first().key

            inactive_keys = APIKey.objects.filter(is_active=False)
            if exclude_key:
                inactive_keys = inactive_keys.exclude(key=exclude_key)
            if inactive_keys.exists():
                return random.choice(list(inactive_keys)).key
        except Exception:
            return None
        return None

    def generate_content(
        self,
        prompt: str,
        tools: Optional[List[Any]] = None,
        file_search_store_name: Optional[str] = None,
    ) -> Any:
        """
        Send a message to the model with optional File Search.
        Args:
            prompt: The user prompt.
            tools: List of tool configurations (optional).
            file_search_store_name: Name of the File Search Store to use (optional).
        """
        config_tools = []

        # Add basic tools if provided
        if tools:
            config_tools.extend(tools)

        # Add File Search tool if a store name is provided
        if file_search_store_name:
            config_tools.append(
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[file_search_store_name]
                    )
                )
            )

        config = types.GenerateContentConfig(
            tools=config_tools if config_tools else None,
            system_instruction=self.system_instruction,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )

            # Extract usage metadata if available
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

            # Attach usage to response object for easy access
            # response.custom_usage = usage # Disabled due to frozen object error

            return response
        except Exception as e:
            print(f"Error generating content: {e}")
            raise


class FileSearchManager:
    """Manages file uploads and indexing for Gemini File Search."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def create_store(self, display_name: str = "Project Store") -> str:
        """Creates a new File Search Store and returns its name (ID)."""
        store = self.client.file_search_stores.create(
            config={"display_name": display_name}
        )
        return store.name

    def upload_file(self, file_path: str, store_name: str) -> bool:
        """Uploads a single file to the store."""
        try:
            operation = self.client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=store_name,
                config={"display_name": os.path.basename(file_path)},
            )

            # Wait for completion
            while not operation.done:
                time.sleep(1)
                operation = self.client.operations.get(operation)

            return True
        except Exception as e:
            print(f"Failed to upload {file_path}: {e}")
            return False

    def delete_store(self, store_name: str):
        """Deletes the store to clean up."""
        try:
            self.client.file_search_stores.delete(
                name=store_name, config={"force": True}
            )
        except Exception as e:
            print(f"Error deleting store {store_name}: {e}")
