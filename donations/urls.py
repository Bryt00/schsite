from django.urls import path
from . import views

urlpatterns = [
    path('', views.cause_list, name='cause_list'),
    path('initiate/', views.initiate_donation, name='initiate_donation'),
    path('initiate/<int:cause_id>/', views.initiate_donation, name='initiate_donation_with_cause'),
    path('verify/<str:reference>/', views.verify_donation, name='verify_donation'),
]
