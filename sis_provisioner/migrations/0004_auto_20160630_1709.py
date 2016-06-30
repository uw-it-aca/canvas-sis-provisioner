# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0003_delete_instructor'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseDelta',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('term_id', models.CharField(unique=True, max_length=20)),
                ('last_query_date', models.DateTimeField()),
                ('changed_since_date', models.DateTimeField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='import',
            name='csv_type',
            field=models.SlugField(max_length=20, choices=[(b'account', b'Curriculum'), (b'user', b'User'), (b'course', b'Course'), (b'coursemember', b'CourseMember'), (b'enrollment', b'Enrollment'), (b'group', b'Group')]),
            preserve_default=True,
        ),
    ]
