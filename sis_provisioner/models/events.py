# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models


class GroupEvent(models.Model):
    """ Representation of a UW GWS Update Event
    """
    group_id = models.CharField(max_length=256)
    reg_id = models.CharField(max_length=32, unique=True)

    class Meta:
        db_table = 'events_groupevent'


class GroupRename(models.Model):
    """ Representation of a UW GWS Update Event
    """
    old_name = models.CharField(max_length=256)
    new_name = models.CharField(max_length=256)

    class Meta:
        db_table = 'events_grouprename'


class EnrollmentLog(models.Model):
    """ Record Event Frequency
    """
    minute = models.IntegerField(default=0)
    event_count = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'events_enrollmentlog'


class GroupLog(models.Model):
    """ Record Event Frequency
    """
    minute = models.IntegerField(default=0)
    event_count = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'events_grouplog'


class InstructorLog(models.Model):
    """ Record Event Frequency
    """
    minute = models.IntegerField(default=0)
    event_count = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'events_instructorlog'


class PersonLog(models.Model):
    """ Record Person Change Event Frequency
    """
    minute = models.IntegerField(default=0)
    event_count = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'events_personlog'
