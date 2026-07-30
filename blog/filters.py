from django_filters import rest_framework as django_filters

from .models import Blog, BlogCategory


class BlogCategoryFilterSet(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    slug = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = BlogCategory
        fields = ["name", "slug"]


class BlogFilterSet(django_filters.FilterSet):
    tags = django_filters.CharFilter(field_name="tags__slug", lookup_expr="iexact")
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = Blog
        fields = ["tags", "category"]
