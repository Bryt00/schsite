from .models import Staff, Subject, Programme, Gallery

def dashboard_callback(request, context):
    """
    Callback function for django-unfold dashboard.
    Returns metrics and counts for the school.
    """
    teaching_count = Staff.objects.filter(staff_type='TEACHING').count()
    support_count = Staff.objects.filter(staff_type='NON_TEACHING').count()
    core_subjects = Subject.objects.filter(is_core=True).count()
    programmes_count = Programme.objects.count()
    gallery_count = Gallery.objects.count()

    # Add useful metrics to context
    context.update({
        "school_stats": [
            {"label": "Teaching Staff", "value": teaching_count, "icon": "school"},
            {"label": "Support Staff", "value": support_count, "icon": "support"},
            {"label": "Core Subjects", "value": core_subjects, "icon": "book-open"},
            {"label": "Programmes", "value": programmes_count, "icon": "academic-cap"},
            {"label": "Gallery Items", "value": gallery_count, "icon": "photograph"},
        ]
    })
    return context
