from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("about", views.about, name="about"),
    path("courses", views.courses, name="courses"),
    path("contact", views.contact, name="contact"),
    path("gallery", views.gallery, name="gallery"),
    path("staff", views.staff, name="staff"),
    path("staff-details/<int:id>/", views.staff_details, name="staff_details"),
    path("event", views.event, name="event"),
    path("event-details/<id>/", views.event_details, name="event_details"),
]