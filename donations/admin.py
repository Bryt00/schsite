from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import DonationCause, Donation

@admin.register(DonationCause)
class DonationCauseAdmin(ModelAdmin):
    list_display = ('title', 'goal_amount', 'is_active', 'created_at')
    search_fields = ('title',)

@admin.register(Donation)
class DonationAdmin(ModelAdmin):
    list_display = ('donor_name', 'amount', 'cause', 'status', 'created_at')
    list_filter = ('status', 'cause')
    search_fields = ('donor_name', 'donor_email', 'reference')
    readonly_fields = ('reference', 'created_at')
