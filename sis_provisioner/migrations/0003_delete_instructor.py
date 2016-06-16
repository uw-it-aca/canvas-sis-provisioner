# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0002_auto_20160603_1058'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Instructor',
        ),
    ]
