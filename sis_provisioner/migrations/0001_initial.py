# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Course'
        db.create_table('sis_provisioner_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=80)),
            ('course_type', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('term_id', self.gf('django.db.models.fields.CharField')(max_length=20, db_index=True)),
            ('primary_id', self.gf('django.db.models.fields.CharField')(max_length=80, null=True)),
            ('xlist_id', self.gf('django.db.models.fields.CharField')(max_length=80, null=True)),
            ('added_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('provisioned_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('provisioned_error', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('provisioned_status', self.gf('django.db.models.fields.CharField')(max_length=512, null=True)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
            ('queue_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
        ))
        db.send_create_signal('sis_provisioner', ['Course'])

        # Adding model 'Enrollment'
        db.create_table('sis_provisioner_enrollment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('reg_id', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')()),
            ('primary_course_id', self.gf('django.db.models.fields.CharField')(max_length=80, null=True)),
            ('instructor_reg_id', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
            ('queue_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
        ))
        db.send_create_signal('sis_provisioner', ['Enrollment'])

        # Adding unique constraint on 'Enrollment', fields ['course_id', 'reg_id']
        db.create_unique('sis_provisioner_enrollment', ['course_id', 'reg_id'])

        # Adding model 'User'
        db.create_table('sis_provisioner_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('net_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('reg_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('added_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('provisioned_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
            ('queue_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
        ))
        db.send_create_signal('sis_provisioner', ['User'])

        # Adding model 'Group'
        db.create_table('sis_provisioner_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('group_id', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('added_by', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('added_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('is_deleted', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('deleted_by', self.gf('django.db.models.fields.CharField')(max_length=20, null=True)),
            ('deleted_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('provisioned_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
            ('queue_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
        ))
        db.send_create_signal('sis_provisioner', ['Group'])

        # Adding unique constraint on 'Group', fields ['course_id', 'group_id', 'role']
        db.create_unique('sis_provisioner_group', ['course_id', 'group_id', 'role'])

        # Adding model 'CourseMember'
        db.create_table('sis_provisioner_coursemember', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('member_type', self.gf('django.db.models.fields.SlugField')(max_length=16)),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('sis_provisioner', ['CourseMember'])

        # Adding model 'Curriculum'
        db.create_table('sis_provisioner_curriculum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('curriculum_abbr', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=20)),
            ('full_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('subaccount_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal('sis_provisioner', ['Curriculum'])

        # Adding model 'Import'
        db.create_table('sis_provisioner_import', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('csv_type', self.gf('django.db.models.fields.SlugField')(max_length=20)),
            ('csv_path', self.gf('django.db.models.fields.CharField')(max_length=80, null=True)),
            ('csv_errors', self.gf('django.db.models.fields.TextField')(null=True)),
            ('added_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
            ('post_status', self.gf('django.db.models.fields.SmallIntegerField')(max_length=3, null=True)),
            ('monitor_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('monitor_status', self.gf('django.db.models.fields.SmallIntegerField')(max_length=3, null=True)),
            ('canvas_id', self.gf('django.db.models.fields.CharField')(max_length=30, null=True)),
            ('canvas_state', self.gf('django.db.models.fields.CharField')(max_length=80, null=True)),
            ('canvas_progress', self.gf('django.db.models.fields.SmallIntegerField')(default=0, max_length=3)),
            ('canvas_errors', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('sis_provisioner', ['Import'])

        # Adding model 'SubAccountOverride'
        db.create_table('sis_provisioner_subaccountoverride', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('subaccount_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('reference_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('sis_provisioner', ['SubAccountOverride'])


    def backwards(self, orm):
        # Removing unique constraint on 'Group', fields ['course_id', 'group_id', 'role']
        db.delete_unique('sis_provisioner_group', ['course_id', 'group_id', 'role'])

        # Removing unique constraint on 'Enrollment', fields ['course_id', 'reg_id']
        db.delete_unique('sis_provisioner_enrollment', ['course_id', 'reg_id'])

        # Deleting model 'Course'
        db.delete_table('sis_provisioner_course')

        # Deleting model 'Enrollment'
        db.delete_table('sis_provisioner_enrollment')

        # Deleting model 'User'
        db.delete_table('sis_provisioner_user')

        # Deleting model 'Group'
        db.delete_table('sis_provisioner_group')

        # Deleting model 'CourseMember'
        db.delete_table('sis_provisioner_coursemember')

        # Deleting model 'Curriculum'
        db.delete_table('sis_provisioner_curriculum')

        # Deleting model 'Import'
        db.delete_table('sis_provisioner_import')

        # Deleting model 'SubAccountOverride'
        db.delete_table('sis_provisioner_subaccountoverride')


    models = {
        'sis_provisioner.course': {
            'Meta': {'object_name': 'Course'},
            'added_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'course_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'course_type': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'primary_id': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'provisioned_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'provisioned_error': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'provisioned_status': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True'}),
            'queue_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'term_id': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'xlist_id': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'})
        },
        'sis_provisioner.coursemember': {
            'Meta': {'object_name': 'CourseMember'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_type': ('django.db.models.fields.SlugField', [], {'max_length': '16'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'sis_provisioner.curriculum': {
            'Meta': {'object_name': 'Curriculum'},
            'curriculum_abbr': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '20'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subaccount_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'sis_provisioner.enrollment': {
            'Meta': {'unique_together': "(('course_id', 'reg_id'),)", 'object_name': 'Enrollment'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor_reg_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {}),
            'primary_course_id': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'queue_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'reg_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        'sis_provisioner.group': {
            'Meta': {'unique_together': "(('course_id', 'group_id', 'role'),)", 'object_name': 'Group'},
            'added_by': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'added_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'deleted_by': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'deleted_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group_id': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_deleted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'provisioned_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'queue_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'sis_provisioner.import': {
            'Meta': {'object_name': 'Import'},
            'added_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'canvas_errors': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'canvas_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'canvas_progress': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'max_length': '3'}),
            'canvas_state': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'csv_errors': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'csv_path': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'csv_type': ('django.db.models.fields.SlugField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monitor_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'monitor_status': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '3', 'null': 'True'}),
            'post_status': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '3', 'null': 'True'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        },
        'sis_provisioner.subaccountoverride': {
            'Meta': {'object_name': 'SubAccountOverride'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reference_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'subaccount_id': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sis_provisioner.user': {
            'Meta': {'object_name': 'User'},
            'added_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'net_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'provisioned_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'queue_id': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'reg_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['sis_provisioner']
