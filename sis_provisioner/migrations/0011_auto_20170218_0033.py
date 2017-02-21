# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-02-18 00:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0010_term_updated_overrides_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='import',
            name='override_sis_stickiness',
            field=models.NullBooleanField(),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='role',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='status',
            field=models.CharField(max_length=16),
        ),
    ]
