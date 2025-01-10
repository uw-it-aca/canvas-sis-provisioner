# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime
from sis_provisioner.dao.canvas import (
    sis_import_by_path, get_sis_import_status, delete_sis_import)
from sis_provisioner.exceptions import MissingImportPathException
from restclients_core.exceptions import DataFailureException
from importlib import import_module
from datetime import datetime, timezone
from logging import getLogger
import json
import re

logger = getLogger(__name__)


class Job(models.Model):
    """ Represents provisioning commands.
    """
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    changed_by = models.CharField(max_length=32)
    changed_date = models.DateTimeField()
    last_run_date = models.DateTimeField(null=True)
    is_active = models.BooleanField(null=True)
    health_status = models.CharField(max_length=512, null=True)
    last_status_date = models.DateTimeField(null=True)

    def json_data(self):
        return {
            'job_id': self.pk,
            'name': self.name,
            'title': self.title,
            'changed_by': self.changed_by,
            'changed_date': localtime(self.changed_date).isoformat() if (
                self.changed_date is not None) else None,
            'last_run_date': localtime(self.last_run_date).isoformat() if (
                self.last_run_date is not None) else None,
            'is_active': self.is_active,
            'health_status': self.health_status,
            'last_status_date': localtime(
                self.last_status_date).isoformat() if (
                    self.last_status_date is not None) else None,
        }


class ImportResource(models.Model):
    PRIORITY_NONE = 0
    PRIORITY_DEFAULT = 1
    PRIORITY_HIGH = 2
    PRIORITY_IMMEDIATE = 3

    PRIORITY_CHOICES = (
        (PRIORITY_NONE, 'none'),
        (PRIORITY_DEFAULT, 'normal'),
        (PRIORITY_HIGH, 'high'),
        (PRIORITY_IMMEDIATE, 'immediate')
    )

    class Meta:
        abstract = True


class ImportManager(models.Manager):
    def find_by_requires_update(self):
        return super(ImportManager, self).get_queryset().filter(
            (Q(canvas_warnings__isnull=True) &
                Q(canvas_errors__isnull=True)) | Q(monitor_status__gte=500),
            canvas_id__isnull=False,
            post_status=200)


class Import(models.Model):
    """ Represents a set of files that have been queued for import.
    """
    CSV_TYPE_CHOICES = (
        ('account', 'sis_provisioner.models.account.Curriculum'),
        ('admin', 'sis_provisioner.models.admin.Admin'),
        ('user', 'sis_provisioner.models.user.User'),
        ('course', 'sis_provisioner.models.course.Course'),
        ('expired_course', 'sis_provisioner.models.course.ExpiredCourse'),
        ('unused_course', 'sis_provisioner.models.course.UnusedCourse'),
        ('enrollment', 'sis_provisioner.models.enrollment.Enrollment'),
        ('invalid_enrollment',
            'sis_provisioner.models.enrollment.InvalidEnrollment'),
        ('group', 'sis_provisioner.models.group.Group')
    )

    csv_type = models.SlugField(max_length=20, choices=CSV_TYPE_CHOICES)
    csv_path = models.CharField(max_length=80, null=True)
    csv_errors = models.TextField(null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    override_sis_stickiness = models.BooleanField(null=True)
    post_status = models.SmallIntegerField(null=True)
    monitor_date = models.DateTimeField(null=True)
    monitor_status = models.SmallIntegerField(null=True)
    canvas_id = models.CharField(max_length=30, null=True)
    canvas_state = models.CharField(max_length=80, null=True)
    canvas_progress = models.SmallIntegerField(default=0)
    canvas_warnings = models.TextField(null=True)
    canvas_errors = models.TextField(null=True)

    objects = ImportManager()

    @property
    def type_name(self):
        model_cls = self.get_csv_type_display()
        if model_cls:
            modname, _, clsname = model_cls.rpartition('.')
            return clsname

    def json_data(self):
        return {
            "queue_id": self.pk,
            "type": self.csv_type,
            "csv_path": self.csv_path,
            "type_name": self.type_name,
            "added_date": localtime(self.added_date).isoformat(),
            "priority": ImportResource.PRIORITY_CHOICES[self.priority][1],
            "override_sis_stickiness": self.override_sis_stickiness,
            "csv_errors": self.csv_errors,
            "post_status": self.post_status,
            "canvas_state": self.canvas_state,
            "canvas_progress": self.canvas_progress,
            "canvas_warnings": self.canvas_warnings,
            "canvas_errors": self.canvas_errors,
        }

    def import_csv(self):
        """
        Imports all csv files for the passed import object, as a zipped
        archive.
        """
        if not self.csv_path:
            raise MissingImportPathException()

        try:
            sis_import = sis_import_by_path(self.csv_path,
                                            self.override_sis_stickiness)
            self.post_status = 200
            self.canvas_id = sis_import.import_id
            self.canvas_state = sis_import.workflow_state
        except DataFailureException as ex:
            self.post_status = ex.status
            self.canvas_errors = ex

        self.save()

    def update_import_status(self):
        """
        Updates import attributes, based on the sis import resource.
        """
        try:
            sis_import = get_sis_import_status(self.canvas_id)
            self.monitor_status = 200
            self.monitor_date = datetime.now(timezone.utc)
            self.canvas_state = sis_import.workflow_state
            self.canvas_progress = sis_import.progress
            self.canvas_warnings = None
            self.canvas_errors = None

            warnings = self._process_warnings(sis_import.processing_warnings)
            if len(warnings):
                self.canvas_warnings = json.dumps(warnings)

            if len(sis_import.processing_errors):
                self.canvas_errors = json.dumps(sis_import.processing_errors)

        except (DataFailureException, KeyError) as ex:
            logger.info('Monitor error: {}'.format(ex))
            return

        if self.is_cleanly_imported():
            self.delete()
        else:
            self.save()
            if self.is_imported():
                self.dequeue_dependent_models()

    def is_completed(self):
        return (self.post_status == 200 and
                self.canvas_progress == 100)

    def is_cleanly_imported(self):
        return (self.is_imported() and
                self.canvas_warnings is None and
                self.canvas_errors is None)

    def is_imported(self):
        return (self.is_completed() and
                self.canvas_state is not None and
                re.match(r'^imported', self.canvas_state) is not None)

    def dependent_model(self):
        model_cls = self.get_csv_type_display()
        try:
            modname, _, clsname = model_cls.rpartition('.')
            module = import_module(modname)
            return getattr(module, clsname)
        except ValueError as ex:
            raise ImportError('Model "{}" not found: {}'.format(model_cls, ex))

    def queued_objects(self):
        return self.dependent_model().objects.queued(self.pk)

    def dequeue_dependent_models(self):
        self.dependent_model().objects.dequeue(self)

    def delete(self, *args, **kwargs):
        self.dequeue_dependent_models()
        if not self.is_completed():
            try:
                delete_sis_import(self.canvas_id)
            except DataFailureException as ex:
                logger.info('PUT sis_import failed: {}'.format(ex))
        return super(Import, self).delete(*args, **kwargs)

    def _process_warnings(self, warnings):
        return [w for w in warnings if not re.search(
            '-(MSIS|THLEAD)-(480|550|601)-', w[-1])]
