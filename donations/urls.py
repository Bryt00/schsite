from django.urls import path
from . import views

urlpatterns = [
    path('', views.cause_list, name='cause_list'),
    path('initiate/', views.initiate_donation, name='initiate_donation'),
    path('initiate/<int:cause_id>/', views.initiate_donation, name='initiate_donation_with_cause'),
    path('verify/<str:reference>/', views.verify_donation, name='verify_donation'),
    path('wassce/', views.wassce_registration, name='wassce_registration'),
    path('wassce/checkout/<str:reference>/', views.wassce_checkout, name='wassce_checkout'),
    path('wassce/initialize/<str:reference>/', views.wassce_initialize_payment, name='wassce_initialize_payment'),
    path('wassce/verify/<str:reference>/', views.verify_wassce_payment, name='verify_wassce_payment'),
    path('wassce/receipt/<str:reference>/', views.wassce_receipt, name='wassce_receipt'),
    path('wassce/receipts/batch/', views.wassce_batch_receipts, name='wassce_batch_receipts'),
    path('wassce/receipts/class/<int:class_id>/', views.wassce_batch_receipts, name='wassce_class_receipts'),
]
