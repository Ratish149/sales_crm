from rest_framework.response import Response
from rest_framework.views import APIView

from advertisement.models import PopUpForm
from appointment.models import Appointment
from contact.models import Contact, NewsLetter
from order.models import Order

# Create your views here.


class UnreadCountView(APIView):
    def get(self, request):
        unread_appointments = Appointment.objects.filter(status="pending").count()
        unread_popup_forms = PopUpForm.objects.filter(is_read=False).count()
        unread_contacts = Contact.objects.filter(is_read=False).count()
        unread_orders = Order.objects.filter(status="pending").count()
        unread_newsletters = NewsLetter.objects.filter(is_read=False).count()

        return Response(
            {
                "unread_appointments": unread_appointments,
                "unread_popup_forms": unread_popup_forms,
                "unread_contacts": unread_contacts,
                "unread_orders": unread_orders,
                "unread_newsletters": unread_newsletters,
            }
        )
