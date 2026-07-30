import django_filters

from .models import GoogleAdSense


class GoogleAdSenseFilter(django_filters.FilterSet):
    publisher_id = django_filters.CharFilter(lookup_expr="icontains")
    is_enabled = django_filters.BooleanFilter()
    autoAds = django_filters.BooleanFilter()

    class Meta:
        model = GoogleAdSense
        fields = ["publisher_id", "is_enabled", "autoAds"]
