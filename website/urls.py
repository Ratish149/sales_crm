# urls.py
from django.urls import path

from . import views

urlpatterns = [
    # 🌈 Theme
    path("themes/", views.ThemeListCreateView.as_view(), name="theme-list-create"),
    path(
        "themes/<int:pk>/",
        views.ThemeRetrieveUpdateDestroyView.as_view(),
        name="theme-detail",
    ),
    path(
        "themes/<int:pk>/publish/",
        views.ThemePublishView.as_view(),
        name="theme-publish",
    ),
    # 📄 Page
    path("pages/", views.PageListCreateView.as_view(), name="page-list-create"),
    path(
        "pages/<slug:slug>/",
        views.PageRetrieveUpdateDestroyView.as_view(),
        name="page-detail",
    ),
    path(
        "pages/<slug:slug>/publish/",
        views.PagePublishView.as_view(),
        name="page-publish",
    ),
    # 🧩 Components
    path(
        "pages/<slug:slug>/components/",
        views.PageComponentListCreateView.as_view(),
        name="component-list-create",
    ),
    path(
        "pages/<slug:slug>/components/<int:component_id>/",
        views.PageComponentRetrieveUpdateDestroyView.as_view(),
        name="component-detail",
    ),
    path(
        "pages/components/<int:id>/publish/",
        views.PageComponentPublishView.as_view(),
        name="component-publish",
    ),
    # 🧭 Navbar
    path("navbar/", views.NavbarView.as_view(), name="navbar"),
    path(
        "navbar/<int:id>/",
        views.NavbarRetrieveUpdateDestroyView.as_view(),
        name="navbar-detail",
    ),
    path(
        "navbar/<int:id>/publish/",
        views.NavbarPublishView.as_view(),
        name="navbar-publish",
    ),
    # 🦶 Footer
    path("footer/", views.FooterView.as_view(), name="footer"),
    path(
        "footer/<int:id>/",
        views.FooterRetrieveUpdateDestroyView.as_view(),
        name="footer-detail",
    ),
    path(
        "footer/<int:id>/publish/",
        views.FooterPublishView.as_view(),
        name="footer-publish",
    ),
    # 🚀 Publish All
    path("publish-all/", views.PublishAllView.as_view(), name="publish-all"),
]
