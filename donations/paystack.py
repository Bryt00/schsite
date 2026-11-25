import requests
from django.conf import settings


class Paystack:
    base_url = 'https://api.paystack.co'

    def __init__(self):
        self.PAYSTACK_SECRET_KEY = (getattr(settings, 'PAYSTACK_SECRET_KEY', '') or '').strip()

    @property
    def key_mode(self):
        if self.PAYSTACK_SECRET_KEY.startswith('sk_live_'):
            return 'LIVE'
        if self.PAYSTACK_SECRET_KEY.startswith('sk_test_'):
            return 'TEST'
        return 'UNKNOWN'

    @property
    def key_prefix(self):
        return self.PAYSTACK_SECRET_KEY[:12] if self.PAYSTACK_SECRET_KEY else '(missing)'

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def fetch_subaccount(self, subaccount_code, timeout=6):
        code = (subaccount_code or '').strip()
        if not code:
            return False, "No subaccount code provided."
        try:
            response = requests.get(
                f"{self.base_url}/subaccount/{code}",
                headers=self._headers(),
                timeout=timeout,
            )
            data = response.json()
            return bool(data.get('status')), data.get('data') or data.get('message')
        except Exception as e:
            return False, str(e)

    def list_subaccounts(self, timeout=6):
        try:
            response = requests.get(
                f"{self.base_url}/subaccount",
                headers=self._headers(),
                timeout=timeout,
            )
            data = response.json()
            if data.get('status') and isinstance(data.get('data'), list):
                return True, data['data']
            return False, data.get('message') or "Could not list subaccounts."
        except Exception as e:
            return False, str(e)

    def initialize_transaction(self, email, amount_pesewas, reference, callback_url=None, subaccount=None, bearer=None, metadata=None):
        path = '/transaction/initialize'
        payload = {
            "email": email,
            "amount": int(amount_pesewas),
            "currency": "GHS",
            "reference": reference,
        }
        if callback_url:
            payload["callback_url"] = callback_url
        subaccount_clean = (subaccount or '').strip()
        if subaccount_clean:
            payload["subaccount"] = subaccount_clean
        if bearer and subaccount_clean:
            payload["bearer"] = bearer
        if metadata:
            payload["metadata"] = metadata

        url = self.base_url + path
        response = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        try:
            data = response.json()
            return data.get('status', False), data.get('data') or data.get('message')
        except Exception as e:
            return False, str(e)

    def verify_payment(self, reference, *args, **kwargs):
        path = f'/transaction/verify/{reference}'
        url = self.base_url + path
        response = requests.get(url, headers=self._headers(), timeout=20)

        if response.status_code == 200:
            response_data = response.json()
            return response_data['status'], response_data['data']
        try:
            response_data = response.json()
            return response_data.get('status', False), response_data.get('message')
        except Exception:
            return False, response.text
