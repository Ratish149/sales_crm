from django.urls import path
from .views import PageComponentListCreateView, PageComponentByTypeView, PageListCreateView, PageRetrieveUpdateDestroyView, NavbarView, FooterView, ThemeListCreateView, ThemeRetrieveUpdateDestroyView

urlpatterns = [
    path("pages/", PageListCreateView.as_view(), name="pages"),
    path("pages/<slug:slug>/",
         PageRetrieveUpdateDestroyView.as_view(), name="page"),
    path("pages/<slug:slug>/components/",
         PageComponentListCreateView.as_view(), name="page-components"),
    path("pages/<slug:slug>/components/<str:component_id>/",
         PageComponentByTypeView.as_view(), name="component-by-type"),
    path("navbar/", NavbarView.as_view(), name="navbar"),
    path("footer/", FooterView.as_view(), name="footer"),
    path("theme/", ThemeListCreateView.as_view(), name="themes"),
    path("theme/<int:theme_id>/",
         ThemeRetrieveUpdateDestroyView.as_view(), name="theme"),
]
