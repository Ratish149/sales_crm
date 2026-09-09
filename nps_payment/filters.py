import json

from django.db.models import Q
from django_filters import rest_framework as django_filters

from .models import NPSTransaction


def parse_json_value(val):
    if not isinstance(val, str):
        return val
    try:
        return json.loads(val.strip())
    except (ValueError, TypeError, json.JSONDecodeError):
        return val


def build_json_q(json_key, raw_val):
    parsed_val = parse_json_value(raw_val)
    str_val = str(raw_val)

    q = Q(**{f"extra_data__{json_key}": parsed_val})
    if parsed_val != str_val and not isinstance(parsed_val, (dict, list)):
        q |= Q(**{f"extra_data__{json_key}": str_val})
    return q


class NPSTransactionFilterSet(django_filters.FilterSet):
    merchant_txn_id = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.CharFilter(lookup_expr="iexact")
    start_date = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    end_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    extra_data = django_filters.CharFilter(method="filter_extra_data")

    class Meta:
        model = NPSTransaction
        fields = ["merchant_txn_id", "status", "start_date", "end_date", "extra_data"]

    def filter_extra_data(self, queryset, name, value):
        if not value:
            return queryset
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return queryset.filter(extra_data__contains=parsed)
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

        if ":" in value:
            k, v = value.split(":", 1)
            return queryset.filter(build_json_q(k.strip(), v.strip()))

        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        request_params = {}
        if hasattr(self, "request") and self.request:
            request_params = self.request.query_params.dict()
        elif isinstance(self.data, dict):
            request_params = self.data

        known_fields = set(self.get_filters().keys()) | {
            "page",
            "page_size",
            "ordering",
            "format",
            "start_date",
            "end_date",
        }

        for key, val in request_params.items():
            if not val or key in known_fields:
                continue
            if key.startswith("extra_data__"):
                json_key = key[len("extra_data__") :]
                queryset = queryset.filter(build_json_q(json_key, val))
            elif not key.startswith("extra_data"):
                queryset = queryset.filter(build_json_q(key, val))

        return queryset
