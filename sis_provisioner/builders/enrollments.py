# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import CourseCSV, SectionCSV, EnrollmentCSV
from sis_provisioner.dao.user import get_person_by_regid
from sis_provisioner.dao.course import is_active_section, section_id_from_url
from sis_provisioner.dao.canvas import ENROLLMENT_ACTIVE, ENROLLMENT_DELETED
from sis_provisioner.exceptions import (
    UserPolicyException, MissingLoginIdException)
from uw_sws.models import Registration, Section
from uw_sws.exceptions import InvalidCanvasIndependentStudyCourse
from restclients_core.exceptions import DataFailureException
from datetime import datetime, timedelta, timezone
from django.conf import settings


class EnrollmentBuilder(Builder):
    """
    Generates import data for each of the passed Enrollment models.
    """
    def _process(self, enrollment):
        if enrollment.queue_id is not None:
            self.queue_id = enrollment.queue_id

        try:
            enrollment.person = get_person_by_regid(enrollment.reg_id)

            course_id = enrollment.course_id
            if enrollment.instructor_reg_id is not None:
                course_id += '-' + enrollment.instructor_reg_id

            section = self.get_section_resource_by_id(course_id)

            if not is_active_section(section):
                return

            enrollment.section = section

        except MissingLoginIdException as err:
            if enrollment.last_modified > self.retry_missing_id:
                self._requeue_enrollment_event(enrollment, err)
            else:
                self._skip_enrollment_event(enrollment, err)
            return
        except (UserPolicyException,
                InvalidCanvasIndependentStudyCourse) as err:
            self._skip_enrollment_event(enrollment, err)
            return
        except DataFailureException as err:
            if err.status == 404:
                self._skip_enrollment_event(enrollment, err)
            else:
                self._requeue_enrollment_event(enrollment, err)
            return

        if enrollment.is_instructor():
            self._process_instructor_enrollment(enrollment)
        else:  # student/auditor
            if len(section.linked_section_urls):
                # Don't enroll students into primary sections
                self._skip_enrollment_event(
                    enrollment, 'Section has linked sections')
            else:
                self._process_student_enrollment(enrollment)

    def _process_instructor_enrollment(self, enrollment):
        if enrollment.section.is_independent_study:
            if enrollment.is_active():
                self.data.add(SectionCSV(section=enrollment.section))
                self.add_teacher_enrollment_data(enrollment.section,
                                                 enrollment.person,
                                                 enrollment.status)
            else:
                enrollment.section.delete_flag = Section.DELETE_FLAG_WITHDRAWN

            # Add or remove independent study course
            self.data.add(CourseCSV(section=enrollment.section))

        elif len(enrollment.section.linked_section_urls):
            # Add/remove primary instructor for each linked section
            for url in enrollment.section.linked_section_urls:
                try:
                    linked_course_id = section_id_from_url(url)
                    linked_section = self.get_section_resource_by_id(
                        linked_course_id)
                    self.data.add(SectionCSV(section=linked_section))
                    self.add_teacher_enrollment_data(linked_section,
                                                     enrollment.person,
                                                     enrollment.status)
                except Exception:
                    continue

        else:
            self.data.add(SectionCSV(section=enrollment.section))
            self.add_teacher_enrollment_data(
                enrollment.section, enrollment.person, enrollment.status)

    def _process_student_enrollment(self, enrollment):
        request_date = enrollment.request_date if (
            enrollment.request_date is not None) else enrollment.last_modified

        registration = Registration(section=enrollment.section,
                                    person=enrollment.person,
                                    is_active=enrollment.is_active(),
                                    request_date=request_date.date(),
                                    request_status=enrollment.status)
        self.add_student_enrollment_data(registration)
        self.data.add(SectionCSV(section=enrollment.section))

        if enrollment.section.is_independent_study:
            self.data.add(CourseCSV(section=enrollment.section))

    def _requeue_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = enrollment.PRIORITY_DEFAULT
        enrollment.save()
        self.logger.info("Requeue enrollment {} in {}: {}".format(
            enrollment.reg_id, enrollment.course_id, err))

    def _skip_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = enrollment.PRIORITY_NONE
        enrollment.save()
        self.logger.info("Skip enrollment {} in {}: {}".format(
            enrollment.reg_id, enrollment.course_id, err))

    def _init_build(self, **kwargs):
        now = datetime.now(timezone.utc)
        timeout = getattr(settings, 'MISSING_LOGIN_ID_RETRY_TIMEOUT', 48)
        self.retry_missing_id = now - timedelta(hours=timeout)


class InvalidEnrollmentBuilder(Builder):
    """
    Generates import data for each of the passed InvalidEnrollment models.
    """
    def _process(self, inv_enrollment):
        now = datetime.now(timezone.utc)
        grace_dt = now - timedelta(days=getattr(
            settings, 'INVALID_ENROLLMENT_GRACE_DAYS', 90))
        status = None

        try:
            # Verify that the check conditions still exist
            if (inv_enrollment.user.is_affiliate_user() or
                    inv_enrollment.user.is_sponsored_user()):
                status = ENROLLMENT_ACTIVE
                if inv_enrollment.deleted_date is not None:
                    inv_enrollment.restored_date = now

            elif inv_enrollment.user.is_student_user():
                if inv_enrollment.found_date < grace_dt:
                    status = ENROLLMENT_DELETED
                    inv_enrollment.deleted_date = now
                    inv_enrollment.restored_date = None

            if status is not None:
                person = get_person_by_regid(inv_enrollment.user.reg_id)
                if self.add_user_data_for_person(person):
                    self.data.add(EnrollmentCSV(
                        section_id=inv_enrollment.section_id,
                        person=person,
                        role=inv_enrollment.role,
                        status=status))
                inv_enrollment.save()

        except DataFailureException as err:
            inv_enrollment.queue_id = None
            inv_enrollment.save()
            self.logger.info('Requeue invalid enrollment {} in {}: {}'.format(
                inv_enrollment.user.reg_id, inv_enrollment.section_id, err))
