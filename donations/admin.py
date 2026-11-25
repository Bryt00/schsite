from decimal import Decimal
from django.contrib import admin, messages
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin
from .models import DonationCause, Donation, SchoolClass, WassceFeeConfig, WasscePayment


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


@admin.register(SchoolClass)
class SchoolClassAdmin(ModelAdmin):
    list_display = (
        'name',
        'programme',
        'sort_order',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'programme')
    search_fields = ('name', 'programme__name')
    ordering = ('sort_order', 'name')



@admin.register(WassceFeeConfig)
class WassceFeeConfigAdmin(ModelAdmin):
    list_display = (
        'academic_year',
        'title',
        'fee_amount',
        'charge_percentage',
        'transaction_charge',
        'total_payable',
        'verified_students_count',
        'net_amount_collected',
        'subaccount_code',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active', 'academic_year')
    search_fields = ('title', 'academic_year', 'subaccount_code')
    readonly_fields = ('paystack_subaccount_status', 'class_payment_breakdown', 'updated_at')
    fieldsets = (
        ("Academic Year & Fee Setup", {
            "fields": ("academic_year", "title", "fee_amount", "is_active", "instructions"),
        }),
        ("Paystack Subaccount & Sender-Borne Charges", {
            "fields": ("subaccount_code", "paystack_subaccount_status", "charge_percentage", "flat_charge"),
        }),
        ("Per-Class Payment Counts (This Academic Year)", {
            "fields": ("class_payment_breakdown", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _verified_count=Count('payments', filter=Q(payments__status='verified')),
            _net_sum=Sum('payments__base_fee', filter=Q(payments__status='verified')),
        )

    @admin.display(description="Paid Students", ordering='_verified_count')
    def verified_students_count(self, obj):
        count = getattr(obj, '_verified_count', 0)
        return f"{count} student{'s' if count != 1 else ''}"

    @admin.display(description="Net Collected", ordering='_net_sum')
    def net_amount_collected(self, obj):
        total = getattr(obj, '_net_sum', None) or Decimal("0.00")
        return f"GHS {total:,.2f}"

    @admin.display(description="Paystack Subaccount Check")
    def paystack_subaccount_status(self, obj):
        from .paystack import Paystack
        paystack = Paystack()
        admin_code = (obj.subaccount_code or "").strip() if obj else ""
        effective = obj.effective_subaccount_code if obj else ""
        source = "Admin field above" if admin_code else ".env (PAYSTACK_WASSCE_SUBACCOUNT)"
        if not effective:
            return format_html(
                '<span style="color:#b91c1c; font-weight:600;">No subaccount configured.</span> '
                'Server key: <code>{}...</code> ({})',
                paystack.key_prefix,
                paystack.key_mode,
            )

        ok, result = paystack.fetch_subaccount(effective, timeout=5)
        if ok and isinstance(result, dict):
            return format_html(
                '<span style="color:#15803d; font-weight:700;">&#10003; Valid &amp; Active</span> '
                '— <code>{}</code> ({}, {}, {} domain) | Source: {} | Server key: <code>{}...</code> ({})',
                effective,
                result.get('business_name') or 'Subaccount',
                result.get('settlement_bank') or '',
                result.get('domain') or paystack.key_mode.lower(),
                source,
                paystack.key_prefix,
                paystack.key_mode,
            )

        avail_ok, avail = paystack.list_subaccounts(timeout=5)
        available_hint = ""
        if avail_ok and isinstance(avail, list):
            codes = [s.get('subaccount_code', '') for s in avail if s.get('subaccount_code')]
            available_hint = (
                f" Available subaccounts on this {paystack.key_mode} key: {', '.join(codes)}"
                if codes
                else f" No subaccounts exist on this {paystack.key_mode} key."
            )
        return format_html(
            '<span style="color:#b91c1c; font-weight:700;">&#10007; Invalid under current server key</span> '
            '— Sent <code>{}</code> (from {}) with key <code>{}...</code> ({}). Paystack said: {}.{}',
            effective,
            source,
            paystack.key_prefix,
            paystack.key_mode,
            str(result),
            available_hint,
        )

    @admin.display(description="Payments Made by Class")
    def class_payment_breakdown(self, obj):
        if not obj or not obj.pk:
            return "Save this configuration first to see per-class payment counts."

        classes = (
            SchoolClass.objects.select_related('programme')
            .annotate(
                paid_count=Count(
                    'wassce_payments',
                    filter=Q(wassce_payments__status='verified', wassce_payments__academic_year=obj.academic_year),
                ),
                pending_count=Count(
                    'wassce_payments',
                    filter=Q(wassce_payments__status='pending', wassce_payments__academic_year=obj.academic_year),
                ),
                net_total=Sum(
                    'wassce_payments__base_fee',
                    filter=Q(wassce_payments__status='verified', wassce_payments__academic_year=obj.academic_year),
                ),
            )
            .order_by('sort_order', 'name')
        )

        if not classes.exists():
            return "No School Classes have been added yet."

        changelist_url = reverse('admin:donations_wasscepayment_changelist')
        rows = format_html_join(
            '',
            '<tr>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0; font-weight:600;">{}</td>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0;">{}</td>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0; font-weight:700; color:#15803d;">{}</td>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0; color:#64748b;">{}</td>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0; font-weight:600;">GHS {}</td>'
            '<td style="padding:8px 12px; border-bottom:1px solid #e2e8f0;">'
            '<a href="{}?school_class__id__exact={}&academic_year={}&status__exact=verified" style="color:#0f7694; font-weight:600; margin-right:12px;">View List</a>'
            '<a href="{}?academic_year={}" target="_blank" style="display:inline-block; padding:3px 9px; border-radius:5px; background:#0f7694; color:#fff; font-weight:600; font-size:0.8rem; text-decoration:none;">Print Class Receipts</a>'
            '</td>'
            '</tr>',
            (
                (
                    sc.name,
                    sc.programme.name if sc.programme else "—",
                    sc.paid_count,
                    sc.pending_count,
                    f"{(sc.net_total or Decimal('0.00')):,.2f}",
                    changelist_url,
                    sc.id,
                    obj.academic_year,
                    reverse('wassce_class_receipts', args=[sc.id]),
                    obj.academic_year,
                )
                for sc in classes
            ),
        )

        return format_html(
            '<div style="overflow-x:auto;">'
            '<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">'
            '<thead>'
            '<tr style="background:#f8fafc; text-align:left;">'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Class</th>'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Programme</th>'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Verified Payments</th>'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Pending</th>'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Net Collected</th>'
            '<th style="padding:8px 12px; border-bottom:2px solid #cbd5e1;">Actions</th>'
            '</tr>'
            '</thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '</div>',
            rows,
        )


@admin.register(WasscePayment)
class WasscePaymentAdmin(ModelAdmin):
    list_display = (
        'surname',
        'other_names',
        'programme',
        'school_class',
        'academic_year',
        'base_fee',
        'transaction_charge',
        'total_amount',
        'status',
        'generate_receipt_button',
        'parent_phone',
        'reference',
        'paid_at',
    )
    list_select_related = ('programme', 'school_class', 'fee_config')
    list_filter = ('academic_year', 'status', 'school_class', 'programme', 'created_at')
    search_fields = ('surname', 'other_names', 'parent_phone', 'parent_name', 'reference', 'academic_year')
    readonly_fields = (
        'reference',
        'academic_year',
        'base_fee',
        'transaction_charge',
        'total_amount',
        'subaccount_code',
        'paid_at',
        'created_at',
        'generate_receipt_button',
    )
    actions = ['generate_receipts_for_selected_payments', 'generate_receipts_for_classes_of_selected']

    @admin.display(description="Receipt")
    def generate_receipt_button(self, obj):
        if not obj or obj.status != 'verified':
            return format_html(
                '<span style="color:#94a3b8; font-size:0.8rem;">{}</span>',
                'Unverified',
            )
        try:
            url = reverse('wassce_receipt', args=[obj.reference])
            return format_html(
                '<a href="{}" target="_blank" style="display:inline-block; padding:4px 10px; border-radius:6px; background:#15803d; color:#fff; font-weight:600; font-size:0.8rem; text-decoration:none;">'
                'Print Receipt'
                '</a>',
                url,
            )
        except Exception:
            return format_html(
                '<span style="color:#94a3b8; font-size:0.8rem;">{}</span>',
                '—',
            )

    @admin.action(description="Generate printable receipt(s) for selected verified student(s)")
    def generate_receipts_for_selected_payments(self, request, queryset):
        verified = queryset.filter(status='verified')
        if not verified.exists():
            self.message_user(request, "None of the selected records have a verified payment status.", level=messages.WARNING)
            return None
        ids = ",".join(str(p.id) for p in verified)
        return redirect(f"{reverse('wassce_batch_receipts')}?payment_ids={ids}")

    @admin.action(description="Generate printable receipts for entire class(es) of selected student(s)")
    def generate_receipts_for_classes_of_selected(self, request, queryset):
        class_ids = ",".join(str(cid) for cid in queryset.values_list('school_class_id', flat=True).distinct())
        return redirect(f"{reverse('wassce_batch_receipts')}?class_ids={class_ids}")




