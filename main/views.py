from django.shortcuts import render, redirect
from django.contrib import messages
from .models import About, Programme, Subject, Staff, Gallery, Event
from .forms import ContactForm


def index(request):
    about_data = About.objects.all()[:1]
    programmes = Programme.objects.all()[:4]
    subjects = Subject.objects.all()[:4]
    staffs = Staff.objects.filter(is_leadership=True).order_by('sort_order', 'id')[:4]
    galleries = Gallery.objects.all()[:4]
    about = None
    if len(about_data) > 0:
        about = about_data[0]
    context = {
        'about': about,
        'programmes': programmes,
        'subjects': subjects,
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
    programmes = Programme.objects.all()[:4]
    subjects = Subject.objects.all()
    context = {
        "subjects": subjects,
        "programmes": programmes,
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
    leadership_staff = Staff.objects.filter(is_leadership=True).order_by('sort_order', 'id')
    teaching_staff = Staff.objects.filter(staff_type='TEACHING').order_by('name')
    non_teaching_staff = Staff.objects.filter(staff_type='NON_TEACHING').order_by('name')
    
    context = {
        "leadership_staff": leadership_staff,
        "teaching_staff": teaching_staff,
        "non_teaching_staff": non_teaching_staff,
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

def staff_details(request, id):
    staff = Staff.objects.get(pk=id)
    # Get subjects taught if it's a teaching staff
    subjects = staff.subjects_taught.all()
    context = {
        "staff": staff,
        "subjects": subjects,
    }
    return render(request, "staff_details.html", context)
