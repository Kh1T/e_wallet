from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Topup, Transaction, User, Wallet


class TopupViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sophea@example.com',
            email='sophea@example.com',
            password='StrongPass123',
            full_name='Sophea Chan',
            phone='012345678',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-TEST123',
            balance=Decimal('10000.00'),
            currency='KHR',
        )

    def test_topup_creates_transaction_and_updates_wallet_balance(self):
        self.client.login(username='sophea@example.com', password='StrongPass123')
        self.client.get(reverse('topup'))
        submission_token = self.client.session['topup_submission_token']

        response = self.client.post(reverse('topup'), {
            'amount': '50000',
            'payment_method': 'aba_mobile',
            'submission_token': submission_token,
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('60000.00'))

        tx = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(tx.transaction_type, 'topup')
        self.assertEqual(tx.status, 'completed')
        self.assertEqual(tx.amount, Decimal('50000'))

        topup = Topup.objects.get(transaction=tx)
        self.assertEqual(topup.payment_method, 'aba_mobile')
        self.assertEqual(topup.provider, 'ABA Mobile')

    def test_topup_rejects_amount_below_minimum(self):
        self.client.login(username='sophea@example.com', password='StrongPass123')
        self.client.get(reverse('topup'))

        response = self.client.post(reverse('topup'), {
            'amount': '999',
            'payment_method': 'aba_mobile',
            'submission_token': self.client.session['topup_submission_token'],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Minimum top up is 1,000 KHR.')
        self.assertEqual(Transaction.objects.count(), 0)

    def test_topup_rejects_duplicate_submission_token(self):
        self.client.login(username='sophea@example.com', password='StrongPass123')
        self.client.get(reverse('topup'))
        submission_token = self.client.session['topup_submission_token']
        payload = {
            'amount': '50000',
            'payment_method': 'aba_mobile',
            'submission_token': submission_token,
        }

        first_response = self.client.post(reverse('topup'), payload)
        second_response = self.client.post(reverse('topup'), payload)

        self.assertRedirects(first_response, reverse('dashboard'))
        self.assertRedirects(second_response, reverse('topup'))
        self.assertEqual(Transaction.objects.count(), 1)
