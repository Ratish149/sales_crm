"""
URL configuration for sales_crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    # Allauth headless for API endpoints
    path("_allauth/", include("allauth.headless.urls")),
    # Regular Allauth for email confirmation and other features
    path("api/", include("accounts.urls")),
    path("api/", include("website.urls")),
    path("api/", include("product.urls")),
    path("api/", include("order.urls")),
    path("api/", include("blog.urls")),
    path("api/", include("whatsapp.urls")),
    path("api/", include("issue_tracking.urls")),
    path("api/", include("advertisement.urls")),
    path("api/", include("contact.urls")),
    path("api/", include("tenants.urls")),
    path("api/", include("team.urls")),
    path("api/", include("testimonial.urls")),
    path("api/", include("faq.urls")),
    path("api/", include("customer.urls")),
    path("api/", include("portfolio.urls")),
    path("api/", include("service.urls")),
    path("api/", include("payment_gateway.urls")),
    path("api/support/", include("support.urls")),
    path("api/", include("logistics.urls")),
    path("api/", include("promo_code.urls")),
    path("api/", include("delivery_charge.urls")),
    path("api/", include("google_analytic.urls")),
    path("api/", include("facebook.urls")),
    path("api/", include("pricing.urls")),
    path("api/", include("appointment.urls")),
    path("api/", include("our_client.urls")),
    path("api/", include("videos.urls")),
    path("api/", include("our_pricing.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
