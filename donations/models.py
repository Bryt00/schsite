from decimal import Decimal, ROUND_CEILING
from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid


def generate_wassce_reference():
    return f"WASSCE-{uuid.uuid4().hex[:10].upper()}"


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


class SchoolClass(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 3 Science 1, 3 Business A, SHS 3 Arts 2")
    programme = models.ForeignKey(
        'main.Programme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='school_classes',
        help_text="Optional: Link this class to a specific Programme so the class dropdown filters by Programme.",
    )
    sort_order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "School Class"
        verbose_name_plural = "School Classes"
        ordering = ['sort_order', 'name']

    def __str__(self):
        if self.programme:
            return f"{self.name} ({self.programme.name})"
        return self.name


class WassceFeeConfig(models.Model):
    title = models.CharField(max_length=200, default="WASSCE Registration Fee")
    academic_year = models.CharField(max_length=50, default="2025/2026", help_text="e.g., 2025/2026")
    fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net WASSCE registration fee in GHS to be received into the subaccount.",
    )
    charge_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.95"),
        help_text="Paystack transaction fee percentage borne by the sender (standard Ghana rate is 1.95%).",
    )
    flat_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Optional additional flat charge in GHS borne by the sender.",
    )
    subaccount_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Paystack Subaccount Code (e.g., ACCT_xxxxxxxxx) for WASSCE collections. Falls back to PAYSTACK_WASSCE_SUBACCOUNT in .env if left blank.",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Optional notice or instructions displayed to parents on the payment page.",
    )
    is_active = models.BooleanField(default=True, help_text="Keep checked for the active WASSCE fee configuration.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WASSCE Fee Configuration"
        verbose_name_plural = "WASSCE Fee Configurations"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.academic_year}) - GHS {self.fee_amount}"

    @property
    def effective_subaccount_code(self):
        code = (self.subaccount_code or "").strip()
        if code:
            return code
        return getattr(settings, 'PAYSTACK_WASSCE_SUBACCOUNT', '').strip()

    @property
    def total_payable(self):
        """
        Gross up the base fee so that after Paystack deducts `charge_percentage` (and `flat_charge`),
        the holding subaccount receives the exact net `fee_amount`.
        Formula: Total = ceil_to_pesewa((fee_amount + flat_charge) / (1 - charge_percentage/100))
        """
        base = Decimal(self.fee_amount or 0)
        flat = Decimal(self.flat_charge or 0)
        rate = Decimal(self.charge_percentage or 0) / Decimal("100")
        if base <= 0:
            return Decimal("0.00")
        if rate <= 0 or rate >= 1:
            return (base + flat).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        gross = (base + flat) / (Decimal("1") - rate)
        return gross.quantize(Decimal("0.01"), rounding=ROUND_CEILING)

    @property
    def transaction_charge(self):
        return (self.total_payable - Decimal(self.fee_amount or 0)).quantize(Decimal("0.01"))


class WasscePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    )

    fee_config = models.ForeignKey(
        WassceFeeConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    academic_year = models.CharField(max_length=50, default="2025/2026", verbose_name="Academic Year")
    surname = models.CharField(max_length=100, verbose_name="Ward's Surname")
    other_names = models.CharField(max_length=150, verbose_name="Ward's Other Names")
    programme = models.ForeignKey(
        'main.Programme',
        on_delete=models.PROTECT,
        related_name='wassce_payments',
        verbose_name="Programme",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name='wassce_payments',
        verbose_name="Class",
    )
    parent_name = models.CharField(max_length=150, blank=True, verbose_name="Parent / Guardian Name")
    parent_phone = models.CharField(max_length=30, verbose_name="Parent / Guardian Phone")
    parent_email = models.EmailField(blank=True, verbose_name="Parent / Guardian Email (Optional)")

    base_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="WASSCE Registration Fee (GHS)")
    transaction_charge = models.DecimalField(max_digits=10, decimal_places=2, help_text="Transaction charge borne by sender (GHS)")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount charged to sender (GHS)")
    subaccount_code = models.CharField(max_length=100, blank=True)

    reference = models.CharField(max_length=100, unique=True, default=generate_wassce_reference)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "WASSCE Payment"
        verbose_name_plural = "WASSCE Payments"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ward_full_name} ({self.school_class.name}) - GHS {self.total_amount} [{self.get_status_display()}]"

    @property
    def ward_full_name(self):
        return f"{self.surname.upper()} {self.other_names}".strip()

    @property
    def payer_email_for_paystack(self):
        if self.parent_email and self.parent_email.strip():
            return self.parent_email.strip()
        clean_ref = "".join(ch for ch in str(self.reference).lower() if ch.isalnum())
        return f"wassce.{clean_ref}@njuascogh.org"

