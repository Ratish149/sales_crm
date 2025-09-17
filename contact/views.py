from rest_framework import generics
from .models import Contact, NewsLetter
from .serializers import ContactSerializer, NewsLetterSerializer
from rest_framework.pagination import PageNumberPagination
from sales_crm.utils.error_handler import (
    duplicate_entry,
    ErrorMessage,
    handle_transaction_errors
)


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ContactCreateView(generics.ListCreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    pagination_class = CustomPagination


class ContactRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class NewsLetterCreateView(generics.ListCreateAPIView):
    queryset = NewsLetter.objects.all()
    serializer_class = NewsLetterSerializer
    pagination_class = CustomPagination

    @handle_transaction_errors
    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        if email and NewsLetter.objects.filter(email__iexact=email, is_subscribed=True).exists():
            return duplicate_entry(
                message=ErrorMessage.DUPLICATE_ENTRY,
                params={
                    'email': 'This email is already subscribed to the newsletter.'}
            )
        return super().create(request, *args, **kwargs)


class NewsLetterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NewsLetter.objects.all()
    serializer_class = NewsLetterSerializer
