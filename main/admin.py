from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin, TabularInline
from tinymce.widgets import TinyMCE
from .models import About, Programme, Subject, Event, Staff, Gallery, ContactMessage

# Register your models here.

class SubjectInline(TabularInline):
    model = Subject.teachers.through
    extra = 1

@admin.register(Programme)
class ProgrammeAdmin(ModelAdmin):
    list_display = ("name", "number_of_subjects", "created_at")
    search_fields = ("name",)

@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    list_display = ("name", "is_core", "author")
    list_filter = ("is_core", "programmes", "author")
    search_fields = ("name", "description")
    filter_horizontal = ("programmes", "teachers")

@admin.register(Staff)
class StaffAdmin(ModelAdmin):
    list_display = ("name", "designation", "staff_type", "is_leadership", "sort_order")
    list_filter = ("staff_type", "is_leadership")
    search_fields = ("name", "designation")
    inlines = [SubjectInline]
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()},
    }
    fieldsets = (
        (None, {
            "fields": (("author", "name"), ("designation", "staff_type"), "image", ("is_leadership", "sort_order"), "parent")
        }),
        ("Biography & Background", {
            "classes": ("tab",),
            "fields": ("bio", "education", "experience_years"),
        }),
        ("Visuals", {
            "classes": ("tab",),
            "fields": (("use_icon", "icon_class"),),
        }),
    )

@admin.register(Gallery)
class GalleryAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(About)
class AboutAdmin(ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }
    list_display = ["title", "subtitle", "author"]
    fields = ["author", "title", "subtitle", "description", "vision", "mission", "image"]

@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ["name", "email", "subject", "created_at"]
    readonly_fields = ["created_at"]
    search_fields = ["name", "email", "subject"]

@admin.register(Event)
class EventAdmin(ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE()}
    }
    list_display=["author","title", "subtitle", ]