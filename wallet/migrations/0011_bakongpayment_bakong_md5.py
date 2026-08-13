# Generated manually to persist the MD5 used by Bakong transaction verification.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0010_bakongpayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='bakongpayment',
            name='bakong_md5',
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True),
        ),
    ]
