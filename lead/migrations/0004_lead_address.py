# Generated by Django 5.1.6 on 2025-03-21 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lead', '0003_lead_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
    ]
