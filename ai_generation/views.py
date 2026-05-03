"""
AI Generation Views

API endpoint to generate blog content using Google Gen AI SDK.
"""

import json
import os

from google import genai
from google.genai import types
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    BlogPromptSerializer,
    BlogResponseSerializer,
    FAQPromptSerializer,
    FAQResponseSerializer,
    PortfolioPromptSerializer,
    PortfolioResponseSerializer,
    ProductImagePromptSerializer,
    ProductResponseSerializer,
    ServicePromptSerializer,
    ServiceResponseSerializer,
    TestimonialPromptSerializer,
    TestimonialResponseSerializer,
)


class GenerateBlogView(APIView):
    """
    POST /api/ai/generate-blog/

    Generate a complete blog post using Google Gemini (google-genai SDK).

    Request body:
    {
        "prompt": "Write a blog about the benefits of drinking water"
    }

    Response:
    {
        "title": "...",
        "content": "...",
        "time_to_read": "5 min read",
        "meta_title": "...",
        "meta_description": "...",
        "tags": ["tag1", "tag2", ...]
    }
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = BlogPromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        print("prompt", prompt)
        api_key = os.getenv("GOOGLE_API_KEY")
        print("API KEY", api_key)
        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
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

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self._build_prompt(prompt),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            blog_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = BlogResponseSerializer(data=blog_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": blog_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_prompt(self, user_prompt: str) -> str:
        return f"""
You are an expert blog writer and SEO specialist. Write in a professional tone.

User request: "{user_prompt}"

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


class GenerateServiceView(APIView):
    """
    POST /api/ai/generate-service/

    Generate a complete service description using Google Gemini.

    Request body:
    {
        "prompt": "Software development services for startups"
    }

    Response:
    {
        "title": "...",
        "description": "...",
        "thumbnail_image_alt_description": "...",
        "meta_title": "...",
        "meta_description": "..."
    }
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = ServicePromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "meta_title": {"type": "STRING"},
                    "meta_description": {"type": "STRING"},
                },
                "required": [
                    "title",
                    "description",
                    "meta_title",
                    "meta_description",
                ],
            }

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self._build_service_prompt(prompt),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            service_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = ServiceResponseSerializer(data=service_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": service_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_service_prompt(self, user_prompt: str) -> str:
        return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{user_prompt}"

Based on the user's request, generate a professional service description.

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
  "meta_description": "SEO meta description, max 160 characters (string)"
}}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""


class GeneratePortfolioView(APIView):
    """
    POST /api/ai/generate-portfolio/

    Generate a complete portfolio item using Google Gemini.

    Request body:
    {
        "prompt": "Mobile app development project for a fintech startup"
    }

    Response:
    {
        "title": "...",
        "content": "...",
        "meta_title": "...",
        "meta_description": "...",
        "tags": ["tag1", "tag2"]
    }
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = PortfolioPromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "content": {"type": "STRING"},
                    "meta_title": {"type": "STRING"},
                    "meta_description": {"type": "STRING"},
                    "tags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                },
                "required": [
                    "title",
                    "content",
                    "meta_title",
                    "meta_description",
                    "tags",
                ],
            }

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self._build_portfolio_prompt(prompt),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            portfolio_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = PortfolioResponseSerializer(data=portfolio_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": portfolio_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_portfolio_prompt(self, user_prompt: str) -> str:
        return f"""
You are an expert copywriter and SEO specialist. Write in a professional tone.

User request: "{user_prompt}"

Based on the user's request, generate a professional portfolio item description.

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


class GenerateProductFromImageView(APIView):
    """
    POST /api/ai/generate-product/

    Generate product details from an image using Google Gemini.

    Request format: multipart/form-data
    - image: Product image file
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = ProductImagePromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data["image"]
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            image_bytes = image_file.read()
            mime_type = image_file.content_type

            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
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

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=[part, self._build_product_prompt()],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            product_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = ProductResponseSerializer(data=product_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": product_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_product_prompt(self) -> str:
        return """
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
  "price": Estimated selling price in numbers only, if applicable (number),
  "market_price": Estimated original market price in numbers only, if applicable (number),
  "weight": "Estimated weight, e.g., '500g' or '1.5kg' (string)",
  "thumbnail_alt_description": "Descriptive alt text for this image, max 100 characters (string)",
  "meta_title": "SEO meta title, max 60 characters (string)",
  "meta_description": "SEO meta description, max 160 characters (string)",
  "suggested_category": "A suggested broad category for the product, e.g., 'Electronics', 'Apparel' (string)"
}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""


class GenerateTestimonialView(APIView):
    """
    POST /api/ai/generate-testimonial/

    Generate testimonial details using Google Gemini.

    Request format: JSON
    {
        "prompt": "Create a testimonial for a satisfied customer of our CRM software",
        "generate_image": false
    }
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = TestimonialPromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "designation": {"type": "STRING"},
                    "comment": {"type": "STRING"},
                },
                "required": [
                    "name",
                    "designation",
                    "comment",
                ],
            }

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self._build_testimonial_prompt(prompt),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            testimonial_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = TestimonialResponseSerializer(data=testimonial_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": testimonial_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_testimonial_prompt(self, user_prompt: str) -> str:
        return f"""
You are an expert copywriter. Write in a professional and authentic tone.

User request: "{user_prompt}"

Based on the user's request, generate a professional customer testimonial.

Requirements:
- Tone: Authentic, believable, and professional
- The comment should be a few sentences long

Return a single valid JSON object with exactly these keys:
{{
  "name": "The customer's full name (string)",
  "designation": "The customer's job title or role and company (string)",
  "comment": "The text of the testimonial (string)"
}}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""


class GenerateFAQView(APIView):
    """
    POST /api/ai/generate-faq/

    Generate FAQ details using Google Gemini.

    Request format: JSON
    {
        "prompt": "Create an FAQ about our new SaaS platform's pricing model."
    }
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = FAQPromptSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data["prompt"]
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return Response(
                {"error": "GOOGLE_API_KEY is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            client = genai.Client(api_key=api_key)

            # Define the expected schema for the response
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "question": {"type": "STRING"},
                    "answer": {"type": "STRING"},
                },
                "required": [
                    "question",
                    "answer",
                ],
            }

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self._build_faq_prompt(prompt),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            raw_text = response.text.strip()

        except Exception as e:
            return Response(
                {"error": "Gemini API call failed.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response
        try:
            faq_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return Response(
                {
                    "error": "AI returned invalid JSON. Please try again.",
                    "detail": str(e),
                    "raw": raw_text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and format output via serializer
        response_serializer = FAQResponseSerializer(data=faq_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "AI response did not match the expected format.",
                "details": response_serializer.errors,
                "raw": faq_data,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def _build_faq_prompt(self, user_prompt: str) -> str:
        return f"""
You are an expert technical writer. Write in a clear, concise, and helpful tone.

User request: "{user_prompt}"

Based on the user's request, generate a frequently asked question and its answer.

Requirements:
- Tone: Clear, helpful, and informative
- The question should be a single sentence
- The answer should be direct and informative (max 500 words)

Return a single valid JSON object with exactly these keys:
{{
  "question": "The FAQ question (string)",
  "answer": "The FAQ answer (string)"
}}

Rules:
- The JSON must be complete and valid — no trailing commas, no comments
"""
