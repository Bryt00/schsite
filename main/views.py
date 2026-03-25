from django.shortcuts import render, redirect
from django.contrib import messages
from .models import About, CourseCategory, Course, Staff, Gallery, Event
from .forms import ContactForm


def index(request):
    about_data = About.objects.all()[:1]
    course_categories = CourseCategory.objects.all()[:4]
    courses = Course.objects.all()[:3]
    staffs = Staff.objects.all()[:4]
    galleries = Gallery.objects.all()[:6]
    about = None
    if len(about_data) > 0:
        about = about_data[0]
    context = {
        'about': about,
        'course_categories': course_categories,
        'courses': courses,
        'staffs': staffs,
        'galleries': galleries,
    }
    return render(request, 'index.html', context)

def about(request):
    about_data = About.objects.all()[:1]
    staffs = Staff.objects.all()[:4]
    about = None
    if len(about_data) > 0:
        about = about_data[0]
    context = {
        'about': about,
        'staffs': staffs,
    }
    return render(request, 'about.html', context)

def courses(request):
    course_categories = CourseCategory.objects.all()[:4]
    courses = Course.objects.all()
    context = {
        "courses": courses,
        "course_categories": course_categories,
    }
    return render(request, 'courses.html', context)

def contact(request):
    return render(request, 'contact.html')

def gallery(request):
    galleries = Gallery.objects.all()
    context = {
        "galleries": galleries,
    }
    return render(request, 'gallery.html', context)

def staff(request):
    staffs = Staff.objects.all()
    context = {
        "staffs": staffs,
    }
    return render(request, 'staff.html', context)

def event(request):
    events = Event.objects.all()
    context = {
        "events": events
    }
    return render(request, 'event.html', context)

def event_details(request, id):
    event = Event.objects.get(pk=id)
    context = {
        "event": event
    }
    return render(request, "event_details.html", context)

