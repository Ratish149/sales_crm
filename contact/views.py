from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework import generics
from .models import Contact, NewsLetter
from .serializers import ContactSerializer, NewsLetterSerializer

# Create your views here.
from rest_framework.pagination import PageNumberPagination


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

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        if email and NewsLetter.objects.filter(email=email, is_subscribed=True).exists():
            raise ValidationError(
                {'email': 'This email is already subscribed to the newsletter.'})
        return super().create(request, *args, **kwargs)


class NewsLetterRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NewsLetter.objects.all()
    serializer_class = NewsLetterSerializer
