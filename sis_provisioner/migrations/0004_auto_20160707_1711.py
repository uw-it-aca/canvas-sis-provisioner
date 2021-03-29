# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0003_delete_instructor'),
    ]

    operations = [
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('term_id', models.CharField(unique=True, max_length=20)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('last_course_search_date', models.DateTimeField(null=True)),
                ('courses_changed_since_date', models.DateTimeField(null=True)),
                ('deleted_unused_courses_date', models.DateTimeField(null=True)),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='import',
            name='csv_type',
            field=models.SlugField(max_length=20, choices=[(b'account', b'Curriculum'), (b'user', b'User'), (b'course', b'Course'), (b'unused_course', b'Term'), (b'coursemember', b'CourseMember'), (b'enrollment', b'Enrollment'), (b'group', b'Group'), (b'eoscourse', b'EOSCourseDelta')]),
            preserve_default=True,
        ),
    ]
