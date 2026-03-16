from django.conf import settings
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import datetime, date
from rest_framework.response import Response
from rest_framework.views import APIView

from advertisement.models import PopUpForm
from appointment.models import Appointment
from contact.models import Contact, NewsLetter
from nepdora_payment.models import TenantCentralPaymentHistory, TenantTransferHistory
from order.models import Order, OrderItem
from payment_gateway.models import PaymentHistory
from product.models import Product


class StatsView(APIView):
    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        month = request.query_params.get("month")
        year = request.query_params.get("year", timezone.now().year)

        filters = Q()

        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                filters &= Q(created_at__range=(start_dt, end_dt))
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
        elif month:
            try:
                filters &= Q(created_at__month=month, created_at__year=year)
                # Calculate start and end for month to generate daily stats
                start_dt = datetime(int(year), int(month), 1)
                if int(month) == 12:
                    end_dt = datetime(int(year) + 1, 1, 1)
                else:
                    end_dt = datetime(int(year), int(month) + 1, 1)
            except ValueError:
                return Response({"error": "Invalid month or year"}, status=400)
        else:
            # Default to last 7 days
            end_dt = timezone.now()
            start_dt = (end_dt - timezone.timedelta(days=6)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            filters &= Q(created_at__range=(start_dt, end_dt))

        # Base Orders Queryset
        orders_qs = Order.objects.filter(filters)
        
        # Valid orders for revenue (excluding cancelled)
        valid_orders_qs = orders_qs.exclude(status="cancelled")

        # Daily Metrics
        daily_stats = []
        current_day = start_dt
        
        # Determine the number of days to iterate
        if month:
            # For month filter, we stop at the last day of the month or today if it's the current month
            today = timezone.now()
            if int(year) == today.year and int(month) == today.month:
                limit_dt = today
            else:
                limit_dt = end_dt - timezone.timedelta(seconds=1)
        else:
            limit_dt = end_dt

        while current_day.date() <= limit_dt.date():
            day_orders = valid_orders_qs.filter(created_at__date=current_day.date())
            daily_revenue = day_orders.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
            daily_count = day_orders.count()
            
            daily_stats.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "revenue": daily_revenue,
                "orders": daily_count
            })
            current_day += timezone.timedelta(days=1)

        # Basic Metrics
        revenue = valid_orders_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        order_count = orders_qs.count()
        delivery_charge = valid_orders_qs.aggregate(Sum("delivery_charge"))["delivery_charge__sum"] or 0
        
        online_payments = valid_orders_qs.filter(
            ~Q(payment_type__in=["cod", "cash"])
        ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        unique_customers = valid_orders_qs.values("customer_phone").distinct().count()
        avg_order_value = valid_orders_qs.aggregate(Avg("total_amount"))["total_amount__avg"] or 0

        # Distribution Channel (POS vs Online)
        channel_dist = orders_qs.values("pos_order").annotate(
            count=Count("id"),
            amount=Sum("total_amount")
        )
        
        # Order Status Distribution
        status_dist = orders_qs.values("status").annotate(
            count=Count("id"),
            amount=Sum("total_amount")
        )

        # Top 5 Cities
        top_cities = valid_orders_qs.exclude(city__isnull=True).exclude(city="").values("city").annotate(
            count=Count("id"),
            amount=Sum("total_amount")
        ).order_by("-count")[:5]

        # Top Selling Products
        # OrderItem relates to Order
        order_items_qs = OrderItem.objects.filter(order__in=valid_orders_qs)
        
        top_selling_products = order_items_qs.values(
            "product__id", "product__name", "product__thumbnail_image"
        ).annotate(
            qty_sold=Sum("quantity"),
            amount=Sum(F("quantity") * F("price"))
        ).order_by("-qty_sold")[:5]
        
        top_selling_products = list(top_selling_products)
        for p in top_selling_products:
            if p.get("product__thumbnail_image"):
                p["product__thumbnail_image"] = request.build_absolute_uri(settings.MEDIA_URL + p["product__thumbnail_image"])

        # Least Selling Products
        least_selling_products = order_items_qs.values(
            "product__id", "product__name", "product__thumbnail_image"
        ).annotate(
            qty_sold=Sum("quantity"),
            amount=Sum(F("quantity") * F("price"))
        ).order_by("qty_sold")[:5]
        
        least_selling_products = list(least_selling_products)
        for p in least_selling_products:
            if p.get("product__thumbnail_image"):
                p["product__thumbnail_image"] = request.build_absolute_uri(settings.MEDIA_URL + p["product__thumbnail_image"])

        return Response({
            "revenue": revenue,
            "orders": order_count,
            "delivery_charge": delivery_charge,
            "online_payments": online_payments,
            "unique_customers": unique_customers,
            "average_order_value": avg_order_value,
            "channel_distribution": channel_dist,
            "status_distribution": status_dist,
            "top_cities": top_cities,
            "top_selling_products": top_selling_products,
            "least_selling_products": least_selling_products,
            "revenue_contribution_by_product": top_selling_products,
            "daily_stats": daily_stats,
        })


class UnreadCountView(APIView):
    def get(self, request):
        unread_appointments = Appointment.objects.filter(status="pending").count()
        unread_popup_forms = PopUpForm.objects.filter(is_read=False).count()
        unread_contacts = Contact.objects.filter(is_read=False).count()
        unread_orders = Order.objects.filter(status="pending").count()
        unread_newsletters = NewsLetter.objects.filter(is_read=False).count()
        unread_own_payment = PaymentHistory.objects.filter(is_read=False).count()
        unread_tenant_transfers = TenantTransferHistory.objects.filter(
            tenant=request.tenant, is_read=False
        ).count()
        unread_tenant_central_payments = TenantCentralPaymentHistory.objects.filter(
            tenant=request.tenant, is_read=False
        ).count()

        return Response(
            {
                "unread_appointments": unread_appointments,
                "unread_popup_forms": unread_popup_forms,
                "unread_contacts": unread_contacts,
                "unread_orders": unread_orders,
                "unread_newsletters": unread_newsletters,
                "unread_own_payment": unread_own_payment,
                "unread_tenant_transfers": unread_tenant_transfers,
                "unread_tenant_payments": unread_tenant_central_payments,
            }
        )
