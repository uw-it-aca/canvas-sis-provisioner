# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CourseMember.is_deleted'
        db.add_column('sis_provisioner_coursemember', 'is_deleted',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'CourseMember.deleted_date'
        db.add_column('sis_provisioner_coursemember', 'deleted_date',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CourseMember.is_deleted'
        db.delete_column('sis_provisioner_coursemember', 'is_deleted')

        # Deleting field 'CourseMember.deleted_date'
        db.delete_column('sis_provisioner_coursemember', 'deleted_date')


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
            'deleted_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_deleted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
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