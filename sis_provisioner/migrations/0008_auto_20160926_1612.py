# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-09-26 23:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0007_auto_20160912_1320'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('course_id', 'reg_id', 'role')]),
        ),
    ]
