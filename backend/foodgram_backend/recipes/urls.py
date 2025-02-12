from django.urls import path
from .views import short_link_redirect

urlpatterns = [
    path('short-link/<int:pk>/', short_link_redirect, name='short-link'),
]
