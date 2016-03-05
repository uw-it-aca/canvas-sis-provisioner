# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalTool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(max_length=200)),
                ('privacy_level', models.CharField(default=b'public', max_length=15, choices=[(b'anonymous', b'Anonymous'), (b'name_only', b'Name Only'), (b'public', b'Public')])),
                ('consumer_key', models.CharField(max_length=100)),
                ('shared_secret', models.CharField(max_length=100)),
                ('url', models.CharField(max_length=100, null=True)),
                ('domain', models.CharField(max_length=100, null=True)),
                ('text', models.CharField(max_length=100, null=True)),
                ('icon_url', models.CharField(max_length=100, null=True)),
                ('not_selectable', models.NullBooleanField(default=True)),
                ('account_navigation_enabled', models.NullBooleanField(default=False)),
                ('account_navigation_url', models.CharField(max_length=100, null=True)),
                ('user_navigation_enabled', models.NullBooleanField(default=False)),
                ('user_navigation_url', models.CharField(max_length=100, null=True)),
                ('course_navigation_enabled', models.NullBooleanField(default=False)),
                ('course_navigation_url', models.CharField(max_length=100, null=True)),
                ('course_navigation_visibility', models.CharField(max_length=10, null=True, choices=[(b'admins', b'Admins'), (b'members', b'Members')])),
                ('course_navigation_default', models.NullBooleanField(default=True)),
                ('editor_button_enabled', models.NullBooleanField(default=False)),
                ('editor_button_url', models.CharField(max_length=100, null=True)),
                ('resource_selection_enabled', models.NullBooleanField(default=False)),
                ('resource_selection_url', models.CharField(max_length=100, null=True)),
                ('changed_by', models.CharField(max_length=32)),
                ('changed_date', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExternalToolCustomField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.IntegerField(unique=True, max_length=100)),
                ('value', models.IntegerField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExternalToolSubaccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subaccount_id', models.IntegerField(unique=True, max_length=15)),
                ('subaccount_sis_id', models.IntegerField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='externaltool',
            name='custom_fields',
            field=models.ManyToManyField(to='sis_provisioner.ExternalToolCustomField'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='externaltool',
            name='subaccounts',
            field=models.ManyToManyField(to='sis_provisioner.ExternalToolSubaccount'),
            preserve_default=True,
        ),
    ]
