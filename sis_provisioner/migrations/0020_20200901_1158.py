# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BLTIKeyStore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('consumer_key', models.CharField(max_length=80, unique=True)),
                ('shared_secret', models.CharField(max_length=80)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
