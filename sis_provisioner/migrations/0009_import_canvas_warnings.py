# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-02-09 21:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0008_auto_20160926_1612'),
    ]

    operations = [
        migrations.AddField(
            model_name='import',
            name='canvas_warnings',
            field=models.TextField(null=True),
        ),
    ]
