"""
AI Generation Views

API endpoints to generate content using Ollama (primary) with Google Gemini as fallback.
"""

import base64
import json
import os
import re
import time

from google import genai
from google.genai import types
from ollama import Client as OllamaClient
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from website.models import SiteConfig

from .serializers import (
    BlogPromptSerializer,
    BlogResponseSerializer,
    FAQPromptSerializer,
    FAQResponseSerializer,
    MultipleBlogResponseSerializer,
    MultipleFAQResponseSerializer,
    MultiplePortfolioResponseSerializer,
    MultipleServiceResponseSerializer,
    MultipleTestimonialResponseSerializer,
    PortfolioPromptSerializer,
    PortfolioResponseSerializer,
    ProductImagePromptSerializer,
    ProductResponseSerializer,
    ServicePromptSerializer,
    ServiceResponseSerializer,
    TestimonialPromptSerializer,
    TestimonialResponseSerializer,
)

OLLAMA_MODEL = "gpt-oss:120b"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
IMAGEN_MODEL = "gemini-2.5-flash-image"


def _parse_json_response(raw_text):
    """
    Try to parse raw_text as JSON.
    Falls back to extracting a JSON block from markdown fences.
    Returns (parsed_data, error_message).
    """
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), None
            except json.JSONDecodeError:
                pass
    return None, raw_text


class BaseGenerativeAPIView(APIView):
    """
    Base view for generating content.

    Primary provider: Ollama (OLLAMA_KEY env var).
    Fallback provider: Google Gemini (GOOGLE_API_KEY env var).

    Subclasses must define:
    - serializer_class
    - response_serializer_class
    - get_response_schema()          — used by Gemini for structured output
    - get_prompt_contents()          — returns a plain-text prompt string
    """

    response_serializer_class = None

    # ------------------------------------------------------------------
    # Business context helper
    # ------------------------------------------------------------------

    def _get_business_context(self):
        """
        Fetch business details from SiteConfig (singleton).
        Returns a formatted string to inject into prompts, or an empty string
        if no config / no details are available.
        """
        try:
            config = SiteConfig.objects.first()
        except Exception:
            return ""

        if not config:
            return ""

        parts = []
        if config.business_name:
            parts.append(f"Business Name: {config.business_name}")
        if config.business_details:
            parts.append(f"Business Details: {config.business_details}")
        if config.address:
            parts.append(f"Address: {config.address}")
        if config.phone:
            parts.append(f"Phone: {config.phone}")
        if config.email:
            parts.append(f"Email: {config.email}")
        if config.working_hours:
            parts.append(f"Working Hours: {config.working_hours}")

        if not parts:
            return ""

        return (
            "\n\nBusiness Context (use this to personalise the content):\n"
            + "\n".join(parts)
        )

    def get_response_schema(self):
        raise NotImplementedError

    def get_prompt_contents(self, validated_data):
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------

    def _call_ollama(self, prompt_text):
        """Call Ollama and return the full raw response text, or raise."""
        api_key = os.environ.get("OLLAMA_KEY")
        if not api_key:
            raise EnvironmentError("OLLAMA_KEY is not configured.")

        client = OllamaClient(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # List available models for debugging
        try:
            available_models = client.list()
            model_names = [m.model for m in available_models.models]
            print(f"[AI] Available Ollama models: {model_names}")
        except Exception as list_err:
            print(f"[AI] Could not list Ollama models: {list_err}")

        messages = [{"role": "user", "content": prompt_text}]

        response = client.chat(OLLAMA_MODEL, messages=messages)
        return response.message.content

    def _call_gemini(self, prompt_text):
        """Call Gemini and return the full raw response text, or raise."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is not configured.")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
                response_schema=self.get_response_schema(),
            ),
        )
        return response.text.strip()

    # ------------------------------------------------------------------
    # Main request handler
    # ------------------------------------------------------------------

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt_text = self.get_prompt_contents(serializer.validated_data)

        # 1. Try Ollama first
        raw_text = None
        provider_used = None
        ollama_error = None

        try:
            raw_text = self._call_ollama(prompt_text)
            provider_used = "ollama"
        except Exception as e:
            ollama_error = str(e)
            print(f"[AI] Ollama failed ({ollama_error}), falling back to Gemini…")

        # 2. Fallback to Gemini if Ollama failed
        if raw_text is None:
            try:
                raw_text = self._call_gemini(prompt_text)
                provider_used = "gemini"
            except Exception as gemini_err:
                return Response(
                    {
                        "error": "Both Ollama and Gemini API calls failed.",
                        "ollama_error": ollama_error,
                        "gemini_error": str(gemini_err),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        print(f"[AI] Response obtained via: {provider_used}")

        # 3. Parse JSON
        parsed_data, bad_raw = _parse_json_response(raw_text)
        if parsed_data is None:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "raw": bad_raw,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Validate output shape
        response_serializer = self.response_serializer_class(data=parsed_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": parsed_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Concrete views
# ---------------------------------------------------------------------------


class GenerateBlogView(BaseGenerativeAPIView):
    """POST /api/ai/generate-blog/"""

    # permission_classes = [IsAuthenticated]
    serializer_class = BlogPromptSerializer
    response_serializer_class = BlogResponseSerializer  # overridden per-request

    # ------------------------------------------------------------------
    # Dynamic schema — single blog vs. batch
    # ------------------------------------------------------------------

    def get_response_schema(self):
        blog_item_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "content": {"type": "STRING"},
                "time_to_read": {"type": "STRING"},
                "meta_title": {"type": "STRING"},
                "meta_description": {"type": "STRING"},
                "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": [
                "title",
                "content",
                "time_to_read",
                "meta_title",
                "meta_description",
                "tags",
            ],
        }
        if getattr(self, "_multiple", False):
            return {
                "type": "OBJECT",
                "properties": {
                    "blogs": {
                        "type": "ARRAY",
                        "items": blog_item_schema,
                    }
                },
                "required": ["blogs"],
            }
        return blog_item_schema

    # ------------------------------------------------------------------
    # Dynamic prompt — single vs. multiple
    # ------------------------------------------------------------------

    def get_prompt_contents(self, validated_data):
        prompt = validated_data["prompt"]
        self._multiple = validated_data.get("multiple", False)
        self._count = validated_data.get("count", 3)

        if self._multiple:
            return f"""
You are an expert blog writer and SEO specialist. Write in a professional tone.

User request: "{prompt}"

Based on the user's request, generate exactly {self._count} complete, unique blog posts on related but distinct subtopics.

Requirements:
- Tone: professional
- Each post: approximately 800 words
- Use proper HTML tags inside each content field: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the blog title inside the content field
- Do NOT wrap content in <html>, <head>, or <body> tags — inner body content only
- Calculate time_to_read based on ~200 words per minute
- Each blog must have a unique title and cover a distinct angle of the topic
- Generate exactly {self._count} blog posts

Return a single valid JSON object with exactly this structure:
{{
  "blogs": [
    {{
      "title": "Blog title (string)",
      "content": "Full blog content in HTML format (string)",
      "time_to_read": "X min read (string)",
      "meta_title": "SEO meta title, max 60 characters (string)",
      "meta_description": "SEO meta description, max 160 characters (string)",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    }}
  ]
}}

Rules:
- tags must be simple, relevant, 1-3 word strings
- The array must contain exactly {self._count} items
- All titles must be unique
- The JSON must be complete and valid — no trailing commas, no comments
"""

        # Single blog
        return f"""
You are an expert blog writer and SEO specialist. Write in a professional tone.

User request: "{prompt}"

Based on the user's request, generate a complete blog post.

Requirements:
- Tone: professional
- Approximate word count: 800 words
- Use proper HTML tags inside the content: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the blog title inside the content field
- Do NOT wrap content in <html>, <head>, or <body> tags — inner body content only
- Calculate time_to_read based on ~200 words per minute (e.g. 800 words → "4 min read")

Return a single valid JSON object with exactly these keys:
{{
  "title": "A compelling, SEO-friendly blog title (string)",
  "content": "Full blog content in HTML format (string)",
  "time_to_read": "X min read (string)",
  "meta_title": "SEO meta title, max 60 characters (string)",
  "meta_description": "SEO meta description, max 160 characters (string)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- tags must be simple, relevant, 1-3 word strings
- The JSON must be complete and valid — no trailing commas, no comments
"""

    # ------------------------------------------------------------------
    # Override post() to select the correct response serializer
    # ------------------------------------------------------------------

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        multiple = serializer.validated_data.get("multiple", False)

        self._multiple = multiple
        self._count = serializer.validated_data.get("count", 3)

        self.response_serializer_class = (
            MultipleBlogResponseSerializer if multiple else BlogResponseSerializer
        )

        return super().post(request)


class GenerateServiceView(BaseGenerativeAPIView):
    """POST /api/ai/generate-service/"""

    # permission_classes = [IsAuthenticated]
    serializer_class = ServicePromptSerializer
    response_serializer_class = ServiceResponseSerializer  # overridden per-request

    # ------------------------------------------------------------------
    # Dynamic schema — single service vs. batch
    # ------------------------------------------------------------------

    def get_response_schema(self):
        service_item_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "description": {"type": "STRING"},
                "meta_title": {"type": "STRING"},
                "meta_description": {"type": "STRING"},
                "service_category_name": {"type": "STRING"},
            },
            "required": [
                "title",
                "description",
                "meta_title",
                "meta_description",
                "service_category_name",
            ],
        }
        if getattr(self, "_multiple", False):
            return {
                "type": "OBJECT",
                "properties": {
                    "services": {
                        "type": "ARRAY",
                        "items": service_item_schema,
                    }
                },
                "required": ["services"],
            }
        return service_item_schema

    # ------------------------------------------------------------------
    # Dynamic prompt — single vs. multiple
    # ------------------------------------------------------------------

    def get_prompt_contents(self, validated_data):
        prompt = validated_data["prompt"]
        self._multiple = validated_data.get("multiple", False)
        self._count = validated_data.get("count", 3)
        business_context = self._get_business_context()

        if self._multiple:
            return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate exactly {self._count} unique, professional service descriptions.
If business context is provided above, tailor each service to that specific business.
Each service must cover a distinct offering or sub-category.

Requirements:
- Tone: professional
- Use proper HTML tags inside each description: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the service title inside the description field
- Do NOT wrap description in <html>, <head>, or <body> tags — inner body content only
- Generate exactly {self._count} services with unique titles

Return a single valid JSON object with exactly this structure:
{{
  "services": [
    {{
      "title": "A professional service name (string)",
      "description": "Detailed service description in HTML format (string)",
      "meta_title": "SEO meta title, max 60 characters (string)",
      "meta_description": "SEO meta description, max 160 characters (string)",
      "service_category_name": "A logical category name, e.g. 'Consulting', 'Development' (string)"
    }}
  ]
}}

Rules:
- The array must contain exactly {self._count} items
- All titles must be unique
- The JSON must be complete and valid — no trailing commas, no comments
"""

        # Single service
        return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate a professional service description.
If business context is provided above, tailor the service to that specific business.

Requirements:
- Tone: professional
- Use proper HTML tags inside the description: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the service title inside the description field
- Do NOT wrap description in <html>, <head>, or <body> tags — inner body content only

Return a single valid JSON object with exactly these keys:
{{
  "title": "A professional service name (string)",
  "description": "Detailed service description in HTML format (string)",
  "meta_title": "SEO meta title, max 60 characters (string)",
  "meta_description": "SEO meta description, max 160 characters (string)",
  "service_category_name": "A logical category name, e.g. 'Consulting', 'Development' (string)"
}}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""

    # ------------------------------------------------------------------
    # Override post() to select the correct response serializer
    # ------------------------------------------------------------------

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        multiple = serializer.validated_data.get("multiple", False)
        self._multiple = multiple
        self._count = serializer.validated_data.get("count", 3)

        self.response_serializer_class = (
            MultipleServiceResponseSerializer if multiple else ServiceResponseSerializer
        )

        return super().post(request)


class GeneratePortfolioView(BaseGenerativeAPIView):
    """POST /api/ai/generate-portfolio/"""

    # permission_classes = [IsAuthenticated]
    serializer_class = PortfolioPromptSerializer
    response_serializer_class = PortfolioResponseSerializer  # overridden per-request

    # ------------------------------------------------------------------
    # Dynamic schema — single portfolio item vs. batch
    # ------------------------------------------------------------------

    def get_response_schema(self):
        portfolio_item_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "content": {"type": "STRING"},
                "meta_title": {"type": "STRING"},
                "meta_description": {"type": "STRING"},
                "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["title", "content", "meta_title", "meta_description", "tags"],
        }
        if getattr(self, "_multiple", False):
            return {
                "type": "OBJECT",
                "properties": {
                    "portfolios": {
                        "type": "ARRAY",
                        "items": portfolio_item_schema,
                    }
                },
                "required": ["portfolios"],
            }
        return portfolio_item_schema

    # ------------------------------------------------------------------
    # Dynamic prompt — single vs. multiple
    # ------------------------------------------------------------------

    def get_prompt_contents(self, validated_data):
        prompt = validated_data["prompt"]
        self._multiple = validated_data.get("multiple", False)
        self._count = validated_data.get("count", 3)
        business_context = self._get_business_context()

        if self._multiple:
            return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate exactly {self._count} unique portfolio item descriptions.
If business context is provided above, frame each item as work done by or for that specific business.
Each portfolio item must represent a distinct project or case study.

Requirements:
- Tone: professional
- Use proper HTML tags inside each content field: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the project title inside the content field
- Do NOT wrap content in <html>, <head>, or <body> tags — inner body content only
- Generate exactly {self._count} portfolio items with unique titles

Return a single valid JSON object with exactly this structure:
{{
  "portfolios": [
    {{
      "title": "A professional project name (string)",
      "content": "Detailed project description and case study in HTML format (string)",
      "meta_title": "SEO meta title, max 60 characters (string)",
      "meta_description": "SEO meta description, max 160 characters (string)",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    }}
  ]
}}

Rules:
- tags must be relevant technologies or project categories (e.g., "Fintech", "React Native", "UI/UX Design")
- The array must contain exactly {self._count} items
- All titles must be unique
- The JSON must be complete and valid — no trailing commas, no comments
"""

        # Single portfolio item
        return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate a professional portfolio item description.
If business context is provided above, frame the portfolio item as work done by or for that specific business.

Requirements:
- Tone: professional
- Use proper HTML tags inside the content: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the project title inside the content field
- Do NOT wrap content in <html>, <head>, or <body> tags — inner body content only

Return a single valid JSON object with exactly these keys:
{{
  "title": "A professional project name (string)",
  "content": "Detailed project description and case study in HTML format (string)",
  "meta_title": "SEO meta title, max 60 characters (string)",
  "meta_description": "SEO meta description, max 160 characters (string)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Rules:
- tags must be relevant technologies or project categories (e.g., "Fintech", "React Native", "UI/UX Design")
- The JSON must be complete and valid — no trailing commas, no comments
"""

    # ------------------------------------------------------------------
    # Override post() to select the correct response serializer
    # ------------------------------------------------------------------

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        multiple = serializer.validated_data.get("multiple", False)
        self._multiple = multiple
        self._count = serializer.validated_data.get("count", 3)

        self.response_serializer_class = (
            MultiplePortfolioResponseSerializer
            if multiple
            else PortfolioResponseSerializer
        )

        return super().post(request)


class GenerateProductFromImageView(BaseGenerativeAPIView):
    """
    POST /api/ai/generate-product/

    Ollama: image is passed as a base64-encoded inline image in the message.
    Gemini: image is passed as a typed Part (bytes).
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = ProductImagePromptSerializer
    response_serializer_class = ProductResponseSerializer

    _PRODUCT_PROMPT_TEXT = """
You are an expert e-commerce copywriter and SEO specialist. Write in a professional tone.

Based on the provided product image, generate detailed product information suitable for an e-commerce platform.

Requirements:
- Tone: professional and compelling
- Use proper HTML tags inside the description: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Do NOT include the product name inside the description field
- Do NOT wrap description in <html>, <head>, or <body> tags — inner body content only

Return a single valid JSON object with exactly these keys:
{
  "name": "A compelling, SEO-friendly product name (string)",
  "description": "Detailed product description highlighting features and benefits in HTML format (string)",
  "price": 0,
  "market_price": 0,
  "weight": "Estimated weight, e.g., '500g' or '1.5kg' (string)",
  "thumbnail_alt_description": "Descriptive alt text for this image, max 100 characters (string)",
  "meta_title": "SEO meta title, max 60 characters (string)",
  "meta_description": "SEO meta description, max 160 characters (string)",
  "suggested_category": "A suggested broad category for the product, e.g., 'Electronics', 'Apparel' (string)"
}

Rules:
- price and market_price must be numbers (use 0 if unknown)
- The JSON must be complete and valid — no trailing commas, no comments
"""

    def get_response_schema(self):
        return {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "description": {"type": "STRING"},
                "price": {"type": "NUMBER"},
                "market_price": {"type": "NUMBER"},
                "weight": {"type": "STRING"},
                "thumbnail_alt_description": {"type": "STRING"},
                "meta_title": {"type": "STRING"},
                "meta_description": {"type": "STRING"},
                "suggested_category": {"type": "STRING"},
            },
            "required": [
                "name",
                "description",
                "thumbnail_alt_description",
                "meta_title",
                "meta_description",
            ],
        }

    def get_prompt_contents(self, validated_data):
        # Not used directly — overriding post() handles both providers.
        return self._PRODUCT_PROMPT_TEXT

    def _call_ollama(self, prompt_text, image_bytes=None, mime_type=None):
        """Override to attach image bytes as base64 for Ollama vision."""
        api_key = os.environ.get("OLLAMA_KEY")
        if not api_key:
            raise EnvironmentError("OLLAMA_KEY is not configured.")

        client = OllamaClient(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # List available models for debugging as requested
        try:
            available_models = client.list()
            model_names = [m.model for m in available_models.models]
            print(f"[AI] Available Ollama models: {model_names}")
        except Exception as list_err:
            print(f"[AI] Could not list Ollama models: {list_err}")

        message = {"role": "user", "content": prompt_text}
        if image_bytes:
            # Convert to base64 string as requested
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            message["images"] = [b64]

        response = client.chat("gemma3:27b", messages=[message])
        return response.message.content

    def _call_gemini_with_image(self, image_bytes, mime_type):
        """Call Gemini with typed image bytes."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is not configured.")

        client = genai.Client(api_key=api_key)
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image_part, self._PRODUCT_PROMPT_TEXT],
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
                response_schema=self.get_response_schema(),
            ),
        )
        return response.text.strip()

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data["image"]
        image_bytes = image_file.read()
        mime_type = image_file.content_type

        raw_text = None
        ollama_error = None
        provider_used = None

        # 1. Try Ollama (vision)
        try:
            raw_text = self._call_ollama(
                self._PRODUCT_PROMPT_TEXT,
                image_bytes=image_bytes,
                mime_type=mime_type,
            )
            provider_used = "ollama"
        except Exception as e:
            ollama_error = str(e)
            print(f"[AI] Ollama failed ({ollama_error}), falling back to Gemini…")

        # 2. Fallback to Gemini
        if raw_text is None:
            try:
                raw_text = self._call_gemini_with_image(image_bytes, mime_type)
                provider_used = "gemini"
            except Exception as gemini_err:
                return Response(
                    {
                        "error": "Both Ollama and Gemini API calls failed.",
                        "ollama_error": ollama_error,
                        "gemini_error": str(gemini_err),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        print(f"[AI] Response obtained via: {provider_used}")

        parsed_data, bad_raw = _parse_json_response(raw_text)
        if parsed_data is None:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "raw": bad_raw,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = self.response_serializer_class(data=parsed_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": parsed_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class GenerateTestimonialView(BaseGenerativeAPIView):
    """POST /api/ai/generate-testimonial/"""

    # permission_classes = [IsAuthenticated]
    serializer_class = TestimonialPromptSerializer
    response_serializer_class = TestimonialResponseSerializer  # overridden per-request

    # ------------------------------------------------------------------
    # Dynamic schema — single testimonial vs. batch
    # ------------------------------------------------------------------

    def get_response_schema(self):
        testimonial_item_schema = {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "designation": {"type": "STRING"},
                "comment": {"type": "STRING"},
                "image": {"type": "STRING"},
            },
            "required": ["name", "designation", "comment"],
        }
        if getattr(self, "_multiple", False):
            return {
                "type": "OBJECT",
                "properties": {
                    "testimonials": {
                        "type": "ARRAY",
                        "items": testimonial_item_schema,
                    }
                },
                "required": ["testimonials"],
            }
        return testimonial_item_schema

    # ------------------------------------------------------------------
    # Dynamic prompt — single vs. multiple
    # ------------------------------------------------------------------

    def get_prompt_contents(self, validated_data):
        prompt = validated_data["prompt"]
        self._multiple = validated_data.get("multiple", False)
        self._count = validated_data.get("count", 3)
        business_context = self._get_business_context()

        if self._multiple:
            return f"""
You are an expert copywriter. Write in a professional and authentic tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate exactly {self._count} unique professional customer testimonials.
If business context is provided above, write each testimonial as if the customer experienced services from that specific business.

Requirements:
- Tone: Authentic, believable, and professional
- Each comment should be 2-4 sentences long
- Each testimonial must be from a distinct, unique person with a different name, designation, and company
- Generate exactly {self._count} testimonials

Return a single valid JSON object with exactly this structure:
{{
  "testimonials": [
    {{"name": "Full Name (string)", "designation": "Job Title, Company (string)", "comment": "Testimonial text (string)"}},
    {{"name": "Full Name (string)", "designation": "Job Title, Company (string)", "comment": "Testimonial text (string)"}}
  ]
}}

Rules:
- The array must contain exactly {self._count} items
- All names and companies must be unique across the list
- The JSON must be complete and valid — no trailing commas, no comments
"""

        # Single testimonial
        return f"""
You are an expert copywriter. Write in a professional and authentic tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate a professional customer testimonial.
If business context is provided above, write the testimonial as if the customer experienced services from that specific business.

Requirements:
- Tone: Authentic, believable, and professional
- The comment should be 2-4 sentences long

Return a single valid JSON object with exactly these keys:
{{
  "name": "The customer's full name (string)",
  "designation": "The customer's job title or role and company (string)",
  "comment": "The text of the testimonial (string)"
}}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""

    # ------------------------------------------------------------------
    # Override post() to select the correct response serializer
    # ------------------------------------------------------------------

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        multiple = serializer.validated_data.get("multiple", False)

        # Set instance-level attributes for get_response_schema() and get_prompt_contents()
        self._multiple = multiple
        self._count = serializer.validated_data.get("count", 3)

        # Point the base class at the right response serializer
        self.response_serializer_class = (
            MultipleTestimonialResponseSerializer
            if multiple
            else TestimonialResponseSerializer
        )

        # 1. Call super().post() to get the text response
        response = super().post(request)

        # 2. If successful, generate images for each testimonial
        if response.status_code == status.HTTP_200_OK:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if api_key:
                client = genai.Client(api_key=api_key)
                if multiple:
                    # Batch generation
                    testimonials = response.data.get("testimonials", [])
                    for t in testimonials:
                        t["image"] = self._generate_profile_image(
                            client, t.get("name"), t.get("designation")
                        )
                        time.sleep(8)
                else:
                    # Single generation
                    response.data["image"] = self._generate_profile_image(
                        client,
                        response.data.get("name"),
                        response.data.get("designation"),
                    )

        return response

    def _generate_profile_image(self, client, name, designation):
        """
        Calls Google's Imagen model to generate a professional profile photo.
        Returns a base64-encoded string of the generated image.
        """
        prompt = (
            f"A professional, high-quality studio portrait of a person named {name or 'Anonymous'}, "
            f"who works as {designation or 'a Professional'}. "
            f"The style should be clean, modern, realistic, and suitable for a professional testimonial profile picture."
        )

        try:
            image_response = client.models.generate_content(
                model=IMAGEN_MODEL,
                contents=[prompt],
            )

            for part in image_response.parts:
                if part.inline_data is not None:
                    # Return base64 directly from inline_data
                    return base64.b64encode(part.inline_data.data).decode("utf-8")

                # Check for other potential data fields in the part
                if hasattr(part, "data") and part.data:
                    return base64.b64encode(part.data).decode("utf-8")

        except Exception as e:
            print(f"[AI] Image generation failed: {e}")

        return None


class GenerateFAQView(BaseGenerativeAPIView):
    """POST /api/ai/generate-faq/"""

    # permission_classes = [IsAuthenticated]
    serializer_class = FAQPromptSerializer
    response_serializer_class = FAQResponseSerializer  # overridden per-request

    # ------------------------------------------------------------------
    # Dynamic schema — depends on whether we are generating 1 or many FAQs
    # ------------------------------------------------------------------

    def get_response_schema(self):
        faq_item_schema = {
            "type": "OBJECT",
            "properties": {
                "question": {"type": "STRING"},
                "answer": {"type": "STRING"},
            },
            "required": ["question", "answer"],
        }
        if getattr(self, "_multiple", False):
            return {
                "type": "OBJECT",
                "properties": {
                    "faqs": {
                        "type": "ARRAY",
                        "items": faq_item_schema,
                    }
                },
                "required": ["faqs"],
            }
        return faq_item_schema

    # ------------------------------------------------------------------
    # Dynamic prompt — single vs. multiple
    # ------------------------------------------------------------------

    def get_prompt_contents(self, validated_data):
        prompt = validated_data["prompt"]
        self._multiple = validated_data.get("multiple", False)
        self._count = validated_data.get("count", 5)
        business_context = self._get_business_context()

        if self._multiple:
            return f"""
You are an expert technical writer. Write in a clear, concise, and helpful tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate exactly {self._count} frequently asked questions and their answers.
If business context is provided above, make all FAQs relevant to that specific business.

Requirements:
- Tone: Clear, helpful, and informative
- Each question must be a single sentence
- IMPORTANT: Each answer must be STRICTLY 1-2 sentences maximum — concise and direct
- Generate exactly {self._count} unique, non-overlapping FAQ pairs

Return a single valid JSON object with exactly this structure:
{{
  "faqs": [
    {{"question": "Question 1 (string)", "answer": "Answer in 1-2 sentences (string)"}},
    {{"question": "Question 2 (string)", "answer": "Answer in 1-2 sentences (string)"}}
  ]
}}

Rules:
- Do NOT write lengthy answers — 1-2 sentences per answer is the hard limit
- The array must contain exactly {self._count} items
- The JSON must be complete and valid — no trailing commas, no comments
"""

        # Single FAQ
        return f"""
You are an expert technical writer. Write in a clear, concise, and helpful tone.

User request: "{prompt}"
{business_context}

Based on the user's request, generate a frequently asked question and its answer.
If business context is provided above, make the FAQ relevant to that specific business.

Requirements:
- Tone: Clear, helpful, and informative
- The question should be a single sentence
- IMPORTANT: The answer must be STRICTLY 1-2 sentences maximum — concise and direct

Return a single valid JSON object with exactly these keys:
{{
  "question": "The FAQ question (string)",
  "answer": "The FAQ answer in 1-2 sentences only (string)"
}}

Rules:
- Do NOT write lengthy answers — 1-2 sentences is the hard limit
- The JSON must be complete and valid — no trailing commas, no comments
"""

    # ------------------------------------------------------------------
    # Override post() to select the correct response serializer
    # ------------------------------------------------------------------

    def post(self, request):
        # Pre-validate to read `multiple` before calling super()
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        multiple = serializer.validated_data.get("multiple", False)

        # Set instance-level attributes so get_response_schema() and
        # get_prompt_contents() both see the correct mode.
        self._multiple = multiple
        self._count = serializer.validated_data.get("count", 5)

        # Point the base class at the right response serializer
        self.response_serializer_class = (
            MultipleFAQResponseSerializer if multiple else FAQResponseSerializer
        )

        # Delegate the rest (provider calls, JSON parsing, validation) to base
        return super().post(request)
