from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce


def get_nps_transactions_total_amount(queryset):
    """
    Calculates total amount and count of filtered NPS transactions using Django ORM aggregation.
    """
    result = queryset.aggregate(
        total_amount=Coalesce(Sum("amount"), Decimal("0.00")),
    )
    return {
        "total_amount": result["total_amount"],
        "count": queryset.count(),
    }
