from django.db import models
from django.utils import timezone
import uuid

class DonationCause(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    goal_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Goal amount in GHS")
    image = models.ImageField(upload_to='donations/causes/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def total_raised(self):
        return self.donation_set.filter(status='verified').aggregate(models.Sum('amount'))['amount__sum'] or 0

class Donation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    )

    cause = models.ForeignKey(DonationCause, on_delete=models.CASCADE, null=True, blank=True)
    donor_name = models.CharField(max_length=100)
    donor_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_name} - GHS {self.amount}"
