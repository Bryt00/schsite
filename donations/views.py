from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from .models import DonationCause, Donation
from .forms import DonationForm

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

from .paystack import Paystack

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
