# Generated by Django 2.0.10 on 2019-02-07 23:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sis_provisioner', '0013_auto_20181024_1731'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='group_id',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='groupevent',
            name='group_id',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='groupmembergroup',
            name='group_id',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='groupmembergroup',
            name='root_group_id',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='import',
            name='csv_type',
            field=models.SlugField(choices=[('account', 'Curriculum'), ('admin', 'Admin'), ('user', 'User'), ('course', 'Course'), ('unused_course', 'Term'), ('coursemember', 'CourseMember'), ('enrollment', 'Enrollment'), ('group', 'Group')], max_length=20),
        ),
    ]