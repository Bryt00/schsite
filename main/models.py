from django.db import models
from django.contrib.auth.models import User



# Create your models here.
class About(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200)
    description = models.TextField()
    vision = models.TextField(blank=True, null=True)
    mission = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='about/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Programme(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='programmes/', default="default.jpg")
    number_of_subjects = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='subjects/')
    is_core = models.BooleanField(default=False, help_text="Core subjects are mandatory for all students")
    syllabus_url = models.URLField(blank=True, null=True, help_text="Link to the official syllabus or resource")
    programmes = models.ManyToManyField(Programme, related_name='subjects', blank=True)
    teachers = models.ManyToManyField('Staff', related_name='subjects_taught', blank=True, limit_choices_to={'staff_type': 'TEACHING'})

    def __str__(self):
        return self.name

class Staff(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    STAFF_TYPES = [
        ('TEACHING', 'Teaching Staff'),
        ('NON_TEACHING', 'Non-Teaching Staff'),
    ]
    staff_type = models.CharField(
        max_length=20,
        choices=STAFF_TYPES,
        default='TEACHING',
        help_text="Categorize staff as teaching or non-teaching"
    )
    image = models.ImageField(upload_to='staff/', blank=True, null=True)
    icon_class = models.CharField(max_length=50, default='fa-user', help_text="FontAwesome class (e.g., fa-user-graduate)")
    use_icon = models.BooleanField(default=True, help_text="Toggle between using an icon or the uploaded image")
    is_leadership = models.BooleanField(default=False, help_text="Show in leadership/position-holding sections")
    sort_order = models.IntegerField(default=10, help_text="Priority in organogram (lower is higher, e.g., 1 for Principal)")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates',
        help_text="The person this staff member reports to (for organogram structure)"
    )
    bio = models.TextField(blank=True, null=True, help_text="A short biography of the staff member")
    education = models.TextField(blank=True, null=True, help_text="Educational background and qualifications")
    experience_years = models.PositiveIntegerField(default=0, help_text="Number of years of professional experience")

    def __str__(self):
        return self.name

class Event(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='events/')
    date_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Gallery(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='gallery/')

    def __str__(self):
        return self.name

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"