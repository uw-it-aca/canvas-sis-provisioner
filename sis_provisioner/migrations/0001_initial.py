# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', models.CharField(unique=True, max_length=80)),
                ('course_type', models.CharField(max_length=16, choices=[(b'sdb', b'SDB'), (b'adhoc', b'Ad Hoc')])),
                ('term_id', models.CharField(max_length=20, db_index=True)),
                ('primary_id', models.CharField(max_length=80, null=True)),
                ('xlist_id', models.CharField(max_length=80, null=True)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('provisioned_date', models.DateTimeField(null=True)),
                ('provisioned_error', models.NullBooleanField()),
                ('provisioned_status', models.CharField(max_length=512, null=True)),
                ('priority', models.SmallIntegerField(default=1, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', models.CharField(max_length=80)),
                ('name', models.CharField(max_length=256)),
                ('member_type', models.SlugField(max_length=16, choices=[(b'uwnetid', b'UWNetID'), (b'eppn', b'ePPN')])),
                ('role', models.CharField(max_length=80)),
                ('is_deleted', models.NullBooleanField()),
                ('deleted_date', models.DateTimeField(null=True, blank=True)),
                ('priority', models.SmallIntegerField(default=0, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Curriculum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('curriculum_abbr', models.SlugField(unique=True, max_length=20)),
                ('full_name', models.CharField(max_length=100)),
                ('subaccount_id', models.CharField(unique=True, max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reg_id', models.CharField(max_length=32, null=True)),
                ('status', models.CharField(max_length=16, choices=[(b'active', b'Active'), (b'inactive', b'Inactive'), (b'deleted', b'Deleted'), (b'completed', b'Completed')])),
                ('course_id', models.CharField(max_length=80)),
                ('last_modified', models.DateTimeField()),
                ('primary_course_id', models.CharField(max_length=80, null=True)),
                ('instructor_reg_id', models.CharField(max_length=32, null=True)),
                ('priority', models.SmallIntegerField(default=1, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', models.CharField(max_length=80)),
                ('group_id', models.CharField(max_length=256)),
                ('role', models.CharField(max_length=80)),
                ('added_by', models.CharField(max_length=20)),
                ('added_date', models.DateTimeField(auto_now_add=True, null=True)),
                ('is_deleted', models.NullBooleanField()),
                ('deleted_by', models.CharField(max_length=20, null=True)),
                ('deleted_date', models.DateTimeField(null=True)),
                ('provisioned_date', models.DateTimeField(null=True)),
                ('priority', models.SmallIntegerField(default=1, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupMemberGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('group_id', models.CharField(max_length=256)),
                ('root_group_id', models.CharField(max_length=256)),
                ('is_deleted', models.NullBooleanField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Import',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('csv_type', models.SlugField(max_length=20, choices=[(b'account', b'Curriculum'), (b'user', b'User'), (b'course', b'Course'), (b'coursemember', b'CourseMember'), (b'enrollment', b'Enrollment'), (b'group', b'Group'), (b'eoscourse', b'EOSCourseDelta')])),
                ('csv_path', models.CharField(max_length=80, null=True)),
                ('csv_errors', models.TextField(null=True)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('priority', models.SmallIntegerField(default=1, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('post_status', models.SmallIntegerField(max_length=3, null=True)),
                ('monitor_date', models.DateTimeField(null=True)),
                ('monitor_status', models.SmallIntegerField(max_length=3, null=True)),
                ('canvas_id', models.CharField(max_length=30, null=True)),
                ('canvas_state', models.CharField(max_length=80, null=True)),
                ('canvas_progress', models.SmallIntegerField(default=0, max_length=3)),
                ('canvas_errors', models.TextField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Instructor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('section_id', models.CharField(max_length=80)),
                ('reg_id', models.CharField(max_length=32)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('title', models.CharField(max_length=128)),
                ('changed_by', models.CharField(max_length=32)),
                ('changed_date', models.DateTimeField()),
                ('last_run_date', models.DateTimeField(null=True)),
                ('is_active', models.NullBooleanField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubAccountOverride',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', models.CharField(max_length=80)),
                ('subaccount_id', models.CharField(max_length=100)),
                ('reference_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TermOverride',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', models.CharField(max_length=80)),
                ('term_sis_id', models.CharField(max_length=24)),
                ('term_name', models.CharField(max_length=24)),
                ('reference_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('net_id', models.CharField(unique=True, max_length=20)),
                ('reg_id', models.CharField(unique=True, max_length=32)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('provisioned_date', models.DateTimeField(null=True)),
                ('priority', models.SmallIntegerField(default=1, choices=[(0, b'none'), (1, b'normal'), (2, b'high'), (3, b'immediate')])),
                ('queue_id', models.CharField(max_length=30, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EnrollmentLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minute', models.IntegerField(default=0)),
                ('event_count', models.SmallIntegerField(default=0)),
            ],
            options={
                'db_table': 'events_enrollmentlog',
            },
        ),
        migrations.CreateModel(
            name='GroupEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_id', models.CharField(max_length=256)),
                ('reg_id', models.CharField(max_length=32, unique=True)),
            ],
            options={
                'db_table': 'events_groupevent',
            },
        ),
        migrations.CreateModel(
            name='GroupLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minute', models.IntegerField(default=0)),
                ('event_count', models.SmallIntegerField(default=0)),
            ],
            options={
                'db_table': 'events_grouplog',
            },
        ),
        migrations.CreateModel(
            name='GroupRename',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_name', models.CharField(max_length=256)),
                ('new_name', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'events_grouprename',
            },
        ),
        migrations.CreateModel(
            name='InstructorLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minute', models.IntegerField(default=0)),
                ('event_count', models.SmallIntegerField(default=0)),
            ],
            options={
                'db_table': 'events_instructorlog',
            },
        ),
        migrations.CreateModel(
            name='PersonLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minute', models.IntegerField(default=0)),
                ('event_count', models.SmallIntegerField(default=0)),
            ],
            options={
                'db_table': 'events_personlog',
            },
        ),
        migrations.AlterUniqueTogether(
            name='instructor',
            unique_together=set([('section_id', 'reg_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together=set([('course_id', 'group_id', 'role')]),
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('course_id', 'reg_id')]),
        ),
    ]
