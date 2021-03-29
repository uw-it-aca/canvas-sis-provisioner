# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='health_status',
            field=models.CharField(max_length=512, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='job',
            name='last_status_date',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
