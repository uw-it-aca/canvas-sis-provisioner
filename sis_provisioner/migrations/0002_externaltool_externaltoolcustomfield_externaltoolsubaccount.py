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
                ('account_id', models.IntegerField(max_length=15)),
                ('config', models.CharField(max_length=2000)),
                ('changed_by', models.CharField(max_length=32)),
                ('changed_date', models.DateTimeField()),
                ('provisioned_date', models.DateTimeField(null=True)),
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
    ]
