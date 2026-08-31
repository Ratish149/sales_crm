from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions

from nepdora_blog.views import CustomPagination

from .filters import NepdoraVideoFilter
from .models import NepdoraVideo
from .serializers import NepdoraVideoSerializer

_VIDEO_FIELDS = ("id", "title", "type", "video_url", "created_at", "updated_at")


class NepdoraVideoListCreateView(generics.ListCreateAPIView):
    queryset = NepdoraVideo.objects.only(*_VIDEO_FIELDS).order_by("-created_at")
    serializer_class = NepdoraVideoSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = NepdoraVideoFilter
    pagination_class = CustomPagination

    search_fields = ["title"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]


class NepdoraVideoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NepdoraVideo.objects.only(*_VIDEO_FIELDS).order_by("-created_at")
    serializer_class = NepdoraVideoSerializer
    permission_classes = [permissions.AllowAny]
