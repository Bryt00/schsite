import sys
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.views.decorators.cache import never_cache
from .models import (
    DonationCause,
    Donation,
    SchoolClass,
    WassceFeeConfig,
    WasscePayment,
    generate_wassce_reference,
)
from .forms import DonationForm, WasscePaymentForm
from .paystack import Paystack


def cause_list(request):
    causes = DonationCause.objects.filter(is_active=True)
    return render(request, 'donations/cause_list.html', {'causes': causes})


def initiate_donation(request, cause_id=None):
    cause = None
    if cause_id:
        cause = get_object_or_404(DonationCause, id=cause_id)

    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            if cause:
                donation.cause = cause
            donation.save()
            return render(request, 'donations/make_payment.html', {
                'donation': donation,
                'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
            })
    else:
        form = DonationForm(initial={'cause': cause})

    return render(request, 'donations/initiate_donation.html', {'form': form, 'cause': cause})


def verify_donation(request, reference):
    donation = get_object_or_404(Donation, reference=reference)
    paystack = Paystack()
    status, result = paystack.verify_payment(reference)

    if status:
        if result['status'] == 'success':
            donation.status = 'verified'
            donation.save()
            messages.success(request, f"Thank you! Your donation of GHS {donation.amount} was successful.")
        else:
            donation.status = 'failed'
            donation.save()
            messages.error(request, f"Payment failed: {result['gateway_response']}")
    else:
        messages.error(request, f"Verification failed: {result}")

    return render(request, 'donations/donation_success.html', {'donation': donation})


@never_cache
def wassce_registration(request):
    fee_config = WassceFeeConfig.objects.filter(is_active=True).first()
    # Never collect WASSCE fees into the main account: keep the portal closed until a subaccount is configured.
    if fee_config and not fee_config.effective_subaccount_code:
        fee_config = None
    school_classes = SchoolClass.objects.filter(is_active=True).select_related('programme').order_by('sort_order', 'name')

    if request.method == 'POST':
        if not fee_config:
            messages.error(request, "WASSCE registration fee has not been configured by the administrator yet.")
            return redirect('wassce_registration')

        form = WasscePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.fee_config = fee_config
            payment.academic_year = fee_config.academic_year
            payment.base_fee = fee_config.fee_amount
            payment.transaction_charge = fee_config.transaction_charge
            payment.total_amount = fee_config.total_payable
            payment.subaccount_code = fee_config.effective_subaccount_code
            payment.save()
            return redirect('wassce_checkout', reference=payment.reference)
    else:
        form = WasscePaymentForm()

    return render(request, 'donations/wassce_registration.html', {
        'form': form,
        'fee_config': fee_config,
        'school_classes': school_classes,
    })


@never_cache
def wassce_checkout(request, reference):
    payment = get_object_or_404(
        WasscePayment.objects.select_related('programme', 'school_class', 'fee_config'),
        reference=reference,
    )
    if payment.status == 'verified':
        return redirect('wassce_receipt', reference=payment.reference)

    return render(request, 'donations/wassce_checkout.html', {
        'payment': payment,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    })


@never_cache
def wassce_initialize_payment(request, reference):
    """
    Initializes transaction directly with Paystack API using the server's Secret Key
    and returns the authorized authorization_url/access_code for checkout.
    """
    try:
        payment = get_object_or_404(
            WasscePayment.objects.select_related('programme', 'school_class', 'fee_config'),
            reference=reference,
        )
        if payment.status == 'verified':
            return JsonResponse({
                'status': True,
                'already_verified': True,
                'redirect_url': reverse('wassce_receipt', args=[payment.reference]),
                'reference': payment.reference,
            })

        # Always sync to the latest configured subaccount code so retries never stay stuck on a stale value.
        active_config = WassceFeeConfig.objects.filter(is_active=True).first()
        effective_subaccount = (
            (active_config.effective_subaccount_code if active_config else "")
            or (payment.fee_config.effective_subaccount_code if payment.fee_config else "")
            or (getattr(settings, 'PAYSTACK_WASSCE_SUBACCOUNT', '') or '').strip()
            or (payment.subaccount_code or '').strip()
        )
        if not effective_subaccount:
            return JsonResponse(
                {'status': False, 'message': 'WASSCE payment subaccount is not configured yet. Please contact administration.'},
                status=400,
            )
        if payment.subaccount_code != effective_subaccount:
            payment.subaccount_code = effective_subaccount
            payment.save(update_fields=['subaccount_code'])

        paystack = Paystack()
        total_pesewas = int(payment.total_amount * 100)
        metadata = {
            "custom_fields": [
                {"display_name": "Ward Surname", "variable_name": "ward_surname", "value": payment.surname},
                {"display_name": "Ward Other Names", "variable_name": "ward_other_names", "value": payment.other_names},
                {"display_name": "Programme", "variable_name": "programme", "value": payment.programme.name if payment.programme else ""},
                {"display_name": "Class", "variable_name": "school_class", "value": payment.school_class.name if payment.school_class else ""},
                {"display_name": "Parent Phone", "variable_name": "parent_phone", "value": payment.parent_phone},
            ]
        }

        def _init_with_current_ref():
            cb_url = request.build_absolute_uri(
                reverse('verify_wassce_payment', args=[payment.reference])
            )
            return paystack.initialize_transaction(
                email=payment.payer_email_for_paystack,
                amount_pesewas=total_pesewas,
                reference=payment.reference,
                callback_url=cb_url,
                subaccount=effective_subaccount,
                bearer="subaccount",
                metadata=metadata,
            )

        status, data = _init_with_current_ref()

        # If the user previously opened Paystack without completing payment, Paystack rejects reusing the reference.
        if not status and isinstance(data, str) and 'duplicate' in data.lower():
            v_status, v_result = paystack.verify_payment(payment.reference)
            if v_status and isinstance(v_result, dict) and v_result.get('status') == 'success':
                paid_pesewas = int(v_result.get('amount', 0))
                paid_currency = v_result.get('currency', 'GHS')
                split_info = v_result.get('subaccount') or {}
                paid_subaccount = split_info.get('subaccount_code', '') if isinstance(split_info, dict) else ''
                if paid_currency == 'GHS' and paid_pesewas >= total_pesewas and paid_subaccount == effective_subaccount:
                    payment.status = 'verified'
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'paid_at'])
                    return JsonResponse({
                        'status': True,
                        'already_verified': True,
                        'redirect_url': reverse('wassce_receipt', args=[payment.reference]),
                        'reference': payment.reference,
                    })

            # Safe to rotate reference and retry initialization cleanly.
            payment.reference = generate_wassce_reference()
            payment.status = 'pending'
            payment.save(update_fields=['reference', 'status'])
            status, data = _init_with_current_ref()

        if status and isinstance(data, dict):
            return JsonResponse({
                'status': True,
                'access_code': data.get('access_code'),
                'authorization_url': data.get('authorization_url'),
                'reference': payment.reference,
                'checkout_url': reverse('wassce_checkout', args=[payment.reference]),
            })
        else:
            err_msg = data if isinstance(data, str) else "Could not initialize transaction with Paystack."
            print(
                f"[WASSCE Paystack Init Error] mode={paystack.key_mode} key={paystack.key_prefix}... "
                f"subaccount={effective_subaccount!r} ref={payment.reference} error={err_msg!r}",
                file=sys.stderr,
            )
            if isinstance(err_msg, str) and 'subaccount' in err_msg.lower():
                err_msg = (
                    f"{err_msg} (Subaccount '{effective_subaccount}' was rejected under the server's "
                    f"{paystack.key_mode} Paystack key '{paystack.key_prefix}...'). "
                    f"Verify PAYSTACK_SECRET_KEY in the server .env and Subaccount Code in WASSCE Fee Settings."
                )
            return JsonResponse({'status': False, 'message': err_msg}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': False, 'message': f"Internal Server Error: {str(e)}"}, status=500)



def verify_wassce_payment(request, reference):
    payment = get_object_or_404(
        WasscePayment.objects.select_related('programme', 'school_class', 'fee_config'),
        reference=reference,
    )
    if payment.status == 'verified':
        return redirect('wassce_receipt', reference=payment.reference)

    paystack = Paystack()
    status, result = paystack.verify_payment(reference)

    if status and isinstance(result, dict):
        expected_pesewas = int(payment.total_amount * 100)
        paid_pesewas = int(result.get('amount', 0))
        paid_currency = result.get('currency', 'GHS')
        split_info = result.get('subaccount') or {}
        paid_subaccount = split_info.get('subaccount_code', '') if isinstance(split_info, dict) else ''
        subaccount_ok = (not payment.subaccount_code) or (paid_subaccount == payment.subaccount_code)

        if result.get('status') == 'success' and not subaccount_ok:
            # Money was taken but not routed to the WASSCE holding subaccount; leave pending for admin reconciliation.
            messages.error(
                request,
                f"Your payment was received but needs manual confirmation by the school. "
                f"Please DO NOT pay again; contact the school with reference {payment.reference}.",
            )
            return redirect('wassce_checkout', reference=payment.reference)

        if result.get('status') == 'success' and paid_currency == 'GHS' and paid_pesewas >= expected_pesewas:
            payment.status = 'verified'
            payment.paid_at = timezone.now()
            payment.save()
            messages.success(
                request,
                f"WASSCE Registration Fee payment for {payment.ward_full_name} has been verified successfully.",
            )
            return redirect('wassce_receipt', reference=payment.reference)
        else:
            payment.status = 'failed'
            payment.save()
            gateway_msg = result.get('gateway_response', 'Transaction was not completed.')
            messages.error(request, f"Payment could not be confirmed: {gateway_msg}")
    else:
        messages.error(request, f"Payment verification failed: {result}")

    return redirect('wassce_checkout', reference=payment.reference)


def wassce_receipt(request, reference):
    payment = get_object_or_404(
        WasscePayment.objects.select_related('programme', 'school_class', 'fee_config'),
        reference=reference,
    )
    if payment.status != 'verified':
        messages.warning(request, "This transaction has not been verified yet. Please complete payment at checkout.")
        return redirect('wassce_checkout', reference=payment.reference)

    return render(request, 'donations/wassce_receipt.html', {'payment': payment})


@staff_member_required
def wassce_batch_receipts(request, class_id=None):
    """
    Generates printable official receipts for:
    - All verified students in a specific SchoolClass (via `class_id` URL param or `?class_ids=1,2`)
    - Or specific verified student payments selected in Admin (`?payment_ids=10,11,12`)
    Optionally filtered by `?academic_year=2025/2026`.
    """
    active_config = WassceFeeConfig.objects.filter(is_active=True).first()
    academic_year = request.GET.get('academic_year')
    if academic_year is None and active_config and not request.GET.get('payment_ids'):
        academic_year = active_config.academic_year

    payments_qs = (
        WasscePayment.objects.filter(status='verified')
        .select_related('programme', 'school_class', 'fee_config')
        .order_by('school_class__sort_order', 'school_class__name', 'surname', 'other_names')
    )

    selected_class = None
    title_label = "All Verified Students"

    payment_ids_param = request.GET.get('payment_ids', '').strip()
    class_ids_param = request.GET.get('class_ids', '').strip()

    if payment_ids_param:
        ids = [int(pk) for pk in payment_ids_param.split(',') if pk.strip().isdigit()]
        payments_qs = payments_qs.filter(id__in=ids)
        title_label = f"Selected Verified Students ({payments_qs.count()})"
    elif class_id:
        selected_class = get_object_or_404(SchoolClass.objects.select_related('programme'), pk=class_id)
        payments_qs = payments_qs.filter(school_class=selected_class)
        title_label = f"Class: {selected_class.name}"
    elif class_ids_param:
        c_ids = [int(pk) for pk in class_ids_param.split(',') if pk.strip().isdigit()]
        payments_qs = payments_qs.filter(school_class_id__in=c_ids)
        class_names = list(SchoolClass.objects.filter(id__in=c_ids).values_list('name', flat=True))
        title_label = f"Classes: {', '.join(class_names)}"

    if academic_year:
        payments_qs = payments_qs.filter(academic_year=academic_year)

    available_years = (
        WasscePayment.objects.filter(status='verified')
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    all_classes = SchoolClass.objects.filter(is_active=True).order_by('sort_order', 'name')

    return render(request, 'donations/wassce_batch_receipts.html', {
        'payments': payments_qs,
        'selected_class': selected_class,
        'selected_academic_year': academic_year or '',
        'available_years': available_years,
        'all_classes': all_classes,
        'title_label': title_label,
        'auto_print': request.GET.get('print') == '1',
    })


