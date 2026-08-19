# Generated manually for adding rejection_reason to IdentityVerification

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0002_identityverification_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='identityverification',
            name='rejection_reason',
            field=models.TextField(blank=True, help_text='Reason for rejection (shown to user)', null=True),
        ),
    ]
