# Generated by Django 5.1.6 on 2025-03-20 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0005_clientfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='phone_number',
            field=models.CharField(blank=True, max_length=254, null=True),
        ),
    ]
