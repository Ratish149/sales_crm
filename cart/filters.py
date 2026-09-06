from django_filters import rest_framework as django_filters

from cart.models import Cart


class CartFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Cart.Status.choices)
    contact_phone = django_filters.CharFilter(
        field_name="contact_phone", lookup_expr="icontains"
    )
    contact_email = django_filters.CharFilter(
        field_name="contact_email", lookup_expr="icontains"
    )
    contact_name = django_filters.CharFilter(
        field_name="contact_name", lookup_expr="icontains"
    )
    date_from = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    last_active_from = django_filters.DateTimeFilter(
        field_name="last_activity_at", lookup_expr="gte"
    )
    last_active_to = django_filters.DateTimeFilter(
        field_name="last_activity_at", lookup_expr="lte"
    )

    class Meta:
        model = Cart
        fields = [
            "status",
            "contact_phone",
            "contact_email",
            "contact_name",
            "date_from",
            "date_to",
            "last_active_from",
            "last_active_to",
        ]
