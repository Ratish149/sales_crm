from django_filters import rest_framework as django_filters
from rest_framework import generics

from .models import Payment
from .serializers import PaymentSerializer, PaymentSmallSerializer


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
            return PaymentSmallSerializer
        return PaymentSerializer


class PaymentRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
