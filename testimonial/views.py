import base64

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales_crm.authentication import TenantJWTAuthentication

from .models import Testimonial
from .serializers import (
    BulkCreateTestimonialSerializer,
    TestimonialSerializer,
)

# Create your views here.


class TestimonialListCreateView(generics.ListCreateAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class TestimonialRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class BulkCreateTestimonialView(APIView):
    """
    POST /api/testimonial/bulk-create/
    Body: { "testimonials": [ { "name": "...", "designation": "...", "comment": "...", "base64_image": "..." }, ... ] }
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = BulkCreateTestimonialSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        testimonials_data = serializer.validated_data.get("testimonials", [])
        created_testimonials = []

        for item in testimonials_data:
            base64_image = item.pop("base64_image", None)
            testimonial = Testimonial.objects.create(**item)

            if base64_image:
                try:
                    # Handle both raw base64 and data URI format
                    if ";base64," in base64_image:
                        format, imgstr = base64_image.split(";base64,")
                        ext = format.split("/")[-1]
                    else:
                        imgstr = base64_image
                        ext = "png"  # Default extension

                    img_data = base64.b64decode(imgstr)
                    file_name = f"testimonial_{testimonial.id}.{ext}"
                    testimonial.image.save(file_name, ContentFile(img_data), save=True)
                except Exception as e:
                    print(
                        f"[Bulk Create] Failed to save image for {testimonial.name}: {e}"
                    )

            created_testimonials.append(testimonial)

        response_data = TestimonialSerializer(created_testimonials, many=True).data
        return Response(
            {"created": len(created_testimonials), "testimonials": response_data},
            status=status.HTTP_201_CREATED,
        )
