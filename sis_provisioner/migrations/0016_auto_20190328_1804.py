# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# Generated by Django 2.0.13 on 2019-03-28 18:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0015_auto_20190304_1832'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='admin',
            name='account_id_str',
        ),
        migrations.AlterField(
            model_name='admin',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sis_provisioner.Account'),
        ),
    ]
