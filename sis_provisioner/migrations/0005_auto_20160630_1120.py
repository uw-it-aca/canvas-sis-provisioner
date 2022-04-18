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
            field=models.BooleanField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='request_date',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
