# Generated by Django 4.2 on 2025-07-26 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0002_prompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='prompt',
            name='footer',
            field=models.TextField(default='Hi', max_length=100000),
        ),
        migrations.AddField(
            model_name='prompt',
            name='header',
            field=models.TextField(default='Hi', max_length=500000),
        ),
    ]
