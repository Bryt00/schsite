from django.contrib import admin
from .models import DonationCause, Donation

@admin.register(DonationCause)
class DonationCauseAdmin(admin.ModelAdmin):
    list_display = ('title', 'goal_amount', 'is_active', 'created_at')
    search_fields = ('title',)

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'amount', 'cause', 'status', 'created_at')
    list_filter = ('status', 'cause')
    search_fields = ('donor_name', 'donor_email', 'reference')
    readonly_fields = ('reference', 'created_at')
