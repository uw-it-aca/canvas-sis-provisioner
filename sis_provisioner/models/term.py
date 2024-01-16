# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from django.utils.timezone import utc
from sis_provisioner.models import ImportResource
from sis_provisioner.dao.term import (
    get_term_by_year_and_quarter, term_date_overrides)
from sis_provisioner.dao.canvas import update_term_overrides
from restclients_core.exceptions import DataFailureException
from datetime import datetime
from logging import getLogger

logger = getLogger(__name__)


class TermManager(models.Manager):
    def update_override_dates(self):
        for term in super().get_queryset().filter(
                updated_overrides_date__isnull=True):

            (year, quarter) = term.term_id.split('-')
            try:
                sws_term = get_term_by_year_and_quarter(year, quarter)
                update_term_overrides(term.term_id,
                                      term_date_overrides(sws_term))
                term.updated_overrides_date = datetime.utcnow().replace(
                    tzinfo=utc)
                term.save()

            except DataFailureException as ex:
                logger.info('Unable to set term overrides: {}'.format(ex))

    def queued(self, queue_id):
        return super().get_queryset().filter(queue_id=queue_id)

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        if sis_import.is_imported():
            # Currently only handles the 'unused_course' type
            kwargs['deleted_unused_courses_date'] = sis_import.monitor_date

        self.queued(sis_import.pk).update(**kwargs)


class Term(ImportResource):
    """ Represents the provisioned state of courses for a term.
    """
    term_id = models.CharField(max_length=20, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    last_course_search_date = models.DateTimeField(null=True)
    courses_changed_since_date = models.DateTimeField(null=True)
    deleted_unused_courses_date = models.DateTimeField(null=True)
    updated_overrides_date = models.DateTimeField(null=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = TermManager()


class TermOverride(models.Model):
    course_id = models.CharField(max_length=80)
    term_sis_id = models.CharField(max_length=24)
    term_name = models.CharField(max_length=24)
    reference_date = models.DateTimeField(auto_now_add=True)
