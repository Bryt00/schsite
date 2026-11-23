from decimal import Decimal
import django.db.models.deletion
from django.db import migrations, models
import donations.models


class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0001_initial'),
        ('main', '0005_remove_coursecategory_author_programme_subject_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g., 3 Science 1, 3 Business A, SHS 3 Arts 2', max_length=100, unique=True)),
                ('sort_order', models.PositiveIntegerField(default=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('programme', models.ForeignKey(blank=True, help_text='Optional: Link this class to a specific Programme so the class dropdown filters by Programme.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='school_classes', to='main.programme')),
            ],
            options={
                'verbose_name': 'School Class',
                'verbose_name_plural': 'School Classes',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='WassceFeeConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='WASSCE Registration Fee', max_length=200)),
                ('academic_year', models.CharField(default='2025/2026', help_text='e.g., 2025/2026', max_length=50)),
                ('fee_amount', models.DecimalField(decimal_places=2, help_text='Net WASSCE registration fee in GHS to be received into the subaccount.', max_digits=10)),
                ('charge_percentage', models.DecimalField(decimal_places=2, default=Decimal('1.95'), help_text='Paystack transaction fee percentage borne by the sender (standard Ghana rate is 1.95%).', max_digits=5)),
                ('flat_charge', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Optional additional flat charge in GHS borne by the sender.', max_digits=8)),
                ('subaccount_code', models.CharField(blank=True, help_text='Paystack Subaccount Code (e.g., ACCT_xxxxxxxxx) for WASSCE collections. Falls back to PAYSTACK_WASSCE_SUBACCOUNT in .env if left blank.', max_length=100)),
                ('instructions', models.TextField(blank=True, help_text='Optional notice or instructions displayed to parents on the payment page.')),
                ('is_active', models.BooleanField(default=True, help_text='Keep checked for the active WASSCE fee configuration.')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'WASSCE Fee Configuration',
                'verbose_name_plural': 'WASSCE Fee Configurations',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='WasscePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(default='2025/2026', max_length=50, verbose_name='Academic Year')),
                ('surname', models.CharField(max_length=100, verbose_name="Ward's Surname")),
                ('other_names', models.CharField(max_length=150, verbose_name="Ward's Other Names")),
                ('parent_name', models.CharField(blank=True, max_length=150, verbose_name='Parent / Guardian Name')),
                ('parent_phone', models.CharField(max_length=30, verbose_name='Parent / Guardian Phone')),
                ('parent_email', models.EmailField(blank=True, max_length=254, verbose_name='Parent / Guardian Email (Optional)')),
                ('base_fee', models.DecimalField(decimal_places=2, help_text='WASSCE Registration Fee (GHS)', max_digits=10)),
                ('transaction_charge', models.DecimalField(decimal_places=2, help_text='Transaction charge borne by sender (GHS)', max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, help_text='Total amount charged to sender (GHS)', max_digits=10)),
                ('subaccount_code', models.CharField(blank=True, max_length=100)),
                ('reference', models.CharField(default=donations.models.generate_wassce_reference, max_length=100, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('verified', 'Verified'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('fee_config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='donations.wasscefeeconfig')),
                ('programme', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wassce_payments', to='main.programme', verbose_name='Programme')),
                ('school_class', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='wassce_payments', to='donations.schoolclass', verbose_name='Class')),
            ],
            options={
                'verbose_name': 'WASSCE Payment',
                'verbose_name_plural': 'WASSCE Payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
