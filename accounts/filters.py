import django_filters
from django_tenants.utils import schema_context

from tenants.models import Client
from website.models import SiteConfig

from .models import CustomUser


class UserFilter(django_filters.FilterSet):
    website_type = django_filters.CharFilter(field_name="website_type")
    enable_pasalbiz = django_filters.BooleanFilter(method="filter_enable_pasalbiz")

    class Meta:
        model = CustomUser
        fields = ["website_type", "enable_pasalbiz"]

    def filter_enable_pasalbiz(self, queryset, name, value):
        if value is None:
            return queryset

        matching_user_ids = []
        clients = Client.objects.exclude(schema_name="public").select_related("owner")
        for client in clients:
            if not client.owner_id:
                continue
            try:
                with schema_context(client.schema_name):
                    config = SiteConfig.objects.first()
                    is_enabled = config.enable_pasalbiz if config else False
                    if is_enabled == value:
                        matching_user_ids.append(client.owner_id)
            except Exception:
                pass

        return queryset.filter(id__in=matching_user_ids)
