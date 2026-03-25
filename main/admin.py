from django.contrib import admin
from django.db import models
from tinymce.widgets import TinyMCE
from .models import About, CourseCategory, Course, Event, Staff, Gallery, ContactMessage
# Register your models here.

admin.site.register(CourseCategory)
admin.site.register(Course)
admin.site.register(Staff)
admin.site.register(Gallery)

@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }
    list_display = ["title", "subtitle", "author"]
    fields = ["author", "title", "subtitle", "description", "vision", "mission", "image"]

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "subject", "created_at"]
    readonly_fields = ["created_at"]
    search_fields = ["name", "email", "subject"]

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }
    list_display=["author","title", "subtitle", ]