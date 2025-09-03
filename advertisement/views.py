from django.shortcuts import render

# Create your views here.


class PopUpCreateView(generics.ListCreateAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer


class PopUpRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopUp.objects.all()
    serializer_class = PopUpSerializer
