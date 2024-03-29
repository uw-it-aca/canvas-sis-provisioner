# Generated by Django 3.2.16 on 2023-01-30 18:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0021_auto_20210504_1907'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='canvas_course_id',
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='created_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='deleted_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='expiration_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='expiration_exc_desc',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='expiration_exc_granted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='sis_provisioner.user'),
        ),
        migrations.AddField(
            model_name='course',
            name='expiration_exc_granted_date',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='term_id',
            field=models.CharField(max_length=30, db_index=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='course_id',
            field=models.CharField(max_length=80, null=True),
        ),
    ]
