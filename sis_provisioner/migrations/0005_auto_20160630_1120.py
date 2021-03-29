# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0004_auto_20160707_1711'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='is_auditor',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='request_date',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
