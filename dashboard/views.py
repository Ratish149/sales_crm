from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser, UserActivity
from tenants.models import Domain

from .serializers import RecentUserSerializer, UserActivityDashboardSerializer


class DashboardStatsSummaryAPIView(APIView):
    def get(self, request):
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_domains = Domain.objects.count()
        total_users = CustomUser.objects.count()

        domains_this_month = Domain.objects.filter(
            created_at__gte=start_of_month
        ).count()

        users_this_month = CustomUser.objects.filter(
            created_at__gte=start_of_month
        ).count()

        return Response({
            "total_domains": total_domains,
            "total_users": total_users,
            "domains_this_month": domains_this_month,
            "users_this_month": users_this_month,
        })


class RecentActivityAPIView(generics.ListAPIView):
    serializer_class = UserActivityDashboardSerializer
    queryset = UserActivity.objects.all().order_by("-timestamp")[:10]


class RecentUsersAPIView(generics.ListAPIView):
    serializer_class = RecentUserSerializer
    queryset = CustomUser.objects.all().order_by("-created_at")[:10]


class UserRegistrationDailyAPIView(APIView):
    def get(self, request):
        now = timezone.now()
        period = request.query_params.get("period", "daily")  # daily, weekly, monthly

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            if period == "monthly":
                start_date = (now - timedelta(days=365)).date()  # Last year
            else:
                # Default to current month for daily and weekly
                start_date = now.replace(day=1).date()

        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = now.date()

        # Select truncation function based on period
        if period == "weekly":
            trunc_func = TruncWeek("created_at")
        elif period == "monthly":
            trunc_func = TruncMonth("created_at")
        else:
            trunc_func = TruncDate("created_at")

        # Group by the selected period and return only those with registrations
        registrations = (
            CustomUser.objects
            .filter(created_at__date__range=[start_date, end_date])
            .annotate(date_group=trunc_func)
            .values("date_group")
            .annotate(count=Count("id"))
            .order_by("date_group")
        )

        # Format results to exclude time
        formatted_registrations = [
            {
                "date": item["date_group"].strftime("%Y-%m-%d") if hasattr(item["date_group"], "strftime") else item["date_group"],
                "count": item["count"]
            }
            for item in registrations
        ]

        # Current month summary
        current_month_total = CustomUser.objects.filter(
            created_at__year=now.year, created_at__month=now.month
        ).count()

        return Response({
            "registrations": formatted_registrations,
            "current_month_total": current_month_total,
            "filter": {
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
            },
        })
