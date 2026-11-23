import requests
from django.conf import settings

class Paystack:
    PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
    base_url = 'https://api.paystack.co'

    def initialize_transaction(self, email, amount_pesewas, reference, subaccount=None, bearer=None, metadata=None):
        path = '/transaction/initialize'
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "amount": int(amount_pesewas),
            "currency": "GHS",
            "reference": reference,
        }
        if subaccount:
            payload["subaccount"] = subaccount
        if bearer:
            payload["bearer"] = bearer
        if metadata:
            payload["metadata"] = metadata

        url = self.base_url + path
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        try:
            data = response.json()
            return data.get('status', False), data.get('data') or data.get('message')
        except Exception as e:
            return False, str(e)

    def verify_payment(self, reference, *args, **kwargs):
        path = f'/transaction/verify/{reference}'
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        url = self.base_url + path
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code == 200:
            response_data = response.json()
            return response_data['status'], response_data['data']
        try:
            response_data = response.json()
            return response_data.get('status', False), response_data.get('message')
        except Exception:
            return False, response.text
