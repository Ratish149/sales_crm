from django_filters import rest_framework as django_filters
from rest_framework import generics

from .models import Payment
from .serializers import PaymentSerializer


# Create your views here.
class PaymentFilterSet(django_filters.FilterSet):
    payment_type = django_filters.CharFilter(
        field_name="payment_type", lookup_expr="iexact"
    )

    class Meta:
        model = Payment
        fields = ["payment_type"]


class PaymentListCreateAPIView(generics.ListCreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = PaymentFilterSet

    def get_serializer_class(self):
        if self.request.method == "GET":
            return PaymentSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            instance_data = response.data
            custom_response = {
                "id": instance_data.get("id"),
                "payment_type": instance_data.get("payment_type"),
                "merchant_code": instance_data.get("merchant_code"),
            }
            response.data = custom_response
        return response


class PaymentRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance_data = response.data
            custom_response = {
                "id": instance_data.get("id"),
                "payment_type": instance_data.get("payment_type"),
                "merchant_code": instance_data.get("merchant_code"),
            }
            response.data = custom_response
        return response
