# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-04-17 20:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0011_auto_20170218_0033'),
    ]

    operations = [
        migrations.RenameField(
            model_name='coursemember',
            old_name='member_type',
            new_name='type',
        ),
    ]
