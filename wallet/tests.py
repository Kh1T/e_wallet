from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password

from .models import Security, Topup, Transaction, Transfer, User, Wallet, IdentityVerification


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

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard'))
        self.assertEqual(
            self.client.session['topup_success_speech'],
            'ការបញ្ចូលលុយបានជោគជ័យ ចំនួន 50000 KHR!',
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('60000.00'))

        tx = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(tx.transaction_type, 'topup')
        self.assertEqual(tx.status, 'completed')
        self.assertEqual(tx.amount, Decimal('50000'))

        topup = Topup.objects.get(transaction=tx)
        self.assertEqual(topup.payment_method, 'aba_mobile')
        self.assertEqual(topup.provider, 'ABA Mobile')

    def test_dashboard_consumes_topup_speech_message(self):
        self.client.login(username='sophea@example.com', password='StrongPass123')
        session = self.client.session
        session['topup_success_speech'] = 'ការបញ្ចូលលុយបានជោគជ័យ ចំនួន 50000 KHR!'
        session.save()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ការបញ្ចូលលុយបានជោគជ័យ ចំនួន 50000 KHR!')
        self.assertNotIn('topup_success_speech', self.client.session)

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


class ReceiveQrTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='qr@example.com',
            email='qr@example.com',
            password='StrongPass123',
            full_name='QR Receiver',
            phone='010203040',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='011 082 544',
            balance=Decimal('5000.00'),
            currency='KHR',
        )

    def test_authenticated_wallet_owner_sees_receive_qr_controls(self):
        self.client.login(username='qr@example.com', password='StrongPass123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="openReceiveQr"')
        self.assertContains(response, 'id="receiveQrModal"')
        self.assertContains(response, 'min="0"')
        self.assertContains(response, 'value="0"')
        self.assertContains(response, 'QR Receiver')
        self.assertContains(response, '011 082 544')

    def test_receive_qr_button_is_hidden_without_a_wallet(self):
        self.wallet.delete()
        self.client.login(username='qr@example.com', password='StrongPass123')

        response = self.client.get(reverse('dashboard'))

        self.assertNotContains(response, 'id="openReceiveQr"')


class TransactionListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dara@example.com',
            email='dara@example.com',
            password='StrongPass123',
            full_name='Dara Sok',
            phone='098765432',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-DARA123',
            balance=Decimal('75000.00'),
            currency='KHR',
        )

        self.sender = User.objects.create_user(
            username='mina@example.com',
            email='mina@example.com',
            password='StrongPass123',
            full_name='Mina Chan',
            phone='011223344',
        )
        self.sender_wallet = Wallet.objects.create(
            user=self.sender,
            wallet_number='WAL-MINA123',
            balance=Decimal('25000.00'),
            currency='KHR',
        )

    def test_transactions_page_renders_wallet_activity(self):
        self.client.login(username='dara@example.com', password='StrongPass123')

        Transaction.objects.create(
            wallet=self.wallet,
            transaction_type='topup',
            amount=Decimal('50000'),
            status='completed',
            description='Top-up via ABA Mobile',
            reference='TOP-TEST123',
        )
        incoming_tx = Transaction.objects.create(
            wallet=self.sender_wallet,
            transaction_type='transfer',
            amount=Decimal('10000'),
            status='completed',
            description='Lunch',
            reference='TRF-TEST123',
        )
        Transfer.objects.create(
            transaction=incoming_tx,
            sender_wallet=self.sender_wallet,
            receiver_wallet=self.wallet,
        )

        response = self.client.get(reverse('transactions'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Top-up via ABA Mobile')
        self.assertContains(response, 'Received from Mina Chan')
        self.assertContains(response, 'TRF-TEST123')


class WalletManagementViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='mona@example.com',
            email='mona@example.com',
            password='StrongPass123',
            full_name='Mona Sok',
            phone='011223344',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-TEST456',
            balance=Decimal('5000.00'),
            currency='KHR',
            status='closed',
        )
        self.second_wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-TEST789',
            balance=Decimal('3000.00'),
            currency='KHR',
        )

    def test_reopen_closed_wallet(self):
        self.client.login(username='mona@example.com', password='StrongPass123')

        response = self.client.post(reverse('wallet_management'), {'action': 'reopen'})

        self.assertRedirects(response, f"{reverse('wallet_management')}?wallet_id={self.wallet.id}")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.status, 'active')

    def test_manage_wallet_can_target_selected_wallet(self):
        self.client.login(username='mona@example.com', password='StrongPass123')

        response = self.client.get(reverse('wallet_management'), {'wallet_id': self.second_wallet.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.second_wallet.wallet_number)

    def test_update_info_form_initializes_with_wallet_currency(self):
        self.client.login(username='mona@example.com', password='StrongPass123')

        response = self.client.get(reverse('wallet_management'), {'action': 'update_info', 'wallet_id': self.second_wallet.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['currency'], self.second_wallet.currency)

    def test_close_wallet_post_keeps_selected_wallet_context(self):
        self.client.login(username='mona@example.com', password='StrongPass123')
        self.second_wallet.balance = Decimal('0.00')
        self.second_wallet.save(update_fields=['balance'])

        response = self.client.post(
            reverse('wallet_management'),
            {'action': 'close', 'wallet_id': self.second_wallet.id},
        )

        self.assertRedirects(response, f"{reverse('wallet_management')}?wallet_id={self.second_wallet.id}")
        self.second_wallet.refresh_from_db()
        self.assertEqual(self.second_wallet.status, 'closed')


class CreateWalletViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='nara@example.com',
            email='nara@example.com',
            password='StrongPass123',
            full_name='Nara Kim',
            phone='055667788',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-TEST789',
            balance=Decimal('2000.00'),
            currency='KHR',
        )

    def test_create_wallet_page_stays_available_before_limit(self):
        IdentityVerification.objects.create(user=self.user, verification_status='verified')
        Wallet.objects.create(user=self.user, wallet_number='WAL-TEST790', balance=Decimal('1000.00'), currency='KHR')
        self.client.login(username='nara@example.com', password='StrongPass123')

        response = self.client.get(reverse('create_wallet'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Wallet')

    def test_unverified_user_cannot_create_wallet(self):
        self.client.login(username='nara@example.com', password='StrongPass123')

        response = self.client.post(reverse('create_wallet'), {'wallet_type': 'separate'})

        self.assertRedirects(response, reverse('kyc'))
        self.assertEqual(Wallet.objects.filter(user=self.user).count(), 1)

    def test_create_separate_wallet_for_existing_user(self):
        IdentityVerification.objects.create(user=self.user, verification_status='verified')
        self.client.login(username='nara@example.com', password='StrongPass123')

        response = self.client.post(reverse('create_wallet'), {'wallet_type': 'separate'})

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(Wallet.objects.filter(user=self.user).count(), 2)


from .models import Security

class TransferSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user@example.com',
            email='user@example.com',
            password='StrongPass123',
            full_name='Test User',
            phone='099112233',
        )
        self.recipient = User.objects.create_user(
            username='recipient@example.com',
            email='recipient@example.com',
            password='StrongPass123',
            full_name='Recipient User',
            phone='099445566',
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_number='WAL-SENDER',
            balance=Decimal('5000.00'),
            currency='KHR',
        )
        self.recipient_wallet = Wallet.objects.create(
            user=self.recipient,
            wallet_number='WAL-RECIPIENT',
            balance=Decimal('1000.00'),
            currency='KHR',
        )
        IdentityVerification.objects.create(user=self.user, verification_status='verified')
        IdentityVerification.objects.create(user=self.recipient, verification_status='verified')
        # Security is created automatically via signal

    def test_set_and_change_pin_via_profile(self):
        self.client.login(username='user@example.com', password='StrongPass123')
        
        # Set a PIN
        response = self.client.post(reverse('profile'), {
            'action': 'change_pin',
            'new_pin': '123456',
            'new_pin2': '123456',
        })
        self.assertRedirects(response, reverse('profile'))
        
        security = Security.objects.get(user=self.user)
        self.assertTrue(security.pin_hash is not None)
        from django.contrib.auth.hashers import check_password
        self.assertTrue(check_password('123456', security.pin_hash))

    def test_send_money_requires_pin_and_otp_if_enabled(self):
        self.client.login(username='user@example.com', password='StrongPass123')
        security = Security.objects.get(user=self.user)
        security.pin_hash = make_password('1234')
        security.otp_enabled = True
        security.save()

        # Try to send money without OTP first
        response = self.client.post(reverse('send'), {
            'recipient_wallet': 'WAL-RECIPIENT',
            'amount': '1000.00',
            'pin': '1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OTP Verification Code')
        
        security.refresh_from_db()
        otp = security.temp_otp
        self.assertTrue(otp is not None)

        # Now send with the correct OTP
        response = self.client.post(reverse('send'), {
            'recipient_wallet': 'WAL-RECIPIENT',
            'amount': '1000.00',
            'pin': '1234',
            'otp_code': otp,
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.wallet.refresh_from_db()
        self.recipient_wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('4000.00'))
        self.assertEqual(self.recipient_wallet.balance, Decimal('2000.00'))

    def test_send_money_incorrect_pin_fails(self):
        self.client.login(username='user@example.com', password='StrongPass123')
        security = Security.objects.get(user=self.user)
        security.pin_hash = make_password('1234')
        security.save()

        response = self.client.post(reverse('send'), {
            'recipient_wallet': 'WAL-RECIPIENT',
            'amount': '1000.00',
            'pin': '9999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid transaction PIN.')

