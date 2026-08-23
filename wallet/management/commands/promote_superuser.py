"""
Promote an existing user to superuser status.

Usage:
    python manage.py promote_superuser admin@gmail.com
"""
from django.core.management.base import BaseCommand
from wallet.models import User


class Command(BaseCommand):
    help = 'Promote an existing user to superuser (staff + superuser privileges)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to promote')

    def handle(self, *args, **options):
        email = options['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email "{email}" does not exist.')
            )
            self.stdout.write(
                self.style.WARNING('Use: python manage.py createsuperuser')
            )
            return

        # Check current status
        if user.is_staff and user.is_superuser:
            self.stdout.write(
                self.style.SUCCESS(f'User "{email}" is already a superuser!')
            )
            return

        # Promote to superuser
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully promoted "{email}" to superuser!')
        )
        self.stdout.write(
            self.style.NOTICE(f'  - is_staff: {user.is_staff}')
        )
        self.stdout.write(
            self.style.NOTICE(f'  - is_superuser: {user.is_superuser}')
        )
