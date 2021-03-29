# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0005_auto_20160630_1120'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='enrollment',
            name='is_auditor',
        ),
        migrations.AddField(
            model_name='enrollment',
            name='role',
            field=models.CharField(default='Student', max_length=32, choices=[(b'Student', b'Student'), (b'Teacher', b'Teacher'), (b'Auditor', b'Auditor')]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='import',
            name='csv_type',
            field=models.SlugField(max_length=20, choices=[(b'account', b'Curriculum'), (b'user', b'User'), (b'course', b'Course'), (b'unused_course', b'Term'), (b'coursemember', b'CourseMember'), (b'enrollment', b'Enrollment'), (b'group', b'Group')]),
            preserve_default=True,
        ),
    ]
