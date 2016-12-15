from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import CourseCSV, SectionCSV
from sis_provisioner.models import PRIORITY_NONE, PRIORITY_DEFAULT
from sis_provisioner.dao.user import get_person_by_regid
from sis_provisioner.dao.course import is_active_section, get_section_by_url
from sis_provisioner.exceptions import UserPolicyException
from restclients.exceptions import (
    DataFailureException, InvalidCanvasIndependentStudyCourse)
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.timezone import utc


class EnrollmentBuilder(Builder):
    """
    Generates import data for each of the passed Enrollment models.
    """
    def _process(self, enrollment):
        try:
            enrollment.person = get_person_by_regid(enrollment.reg_id)

            section = self.get_section_resource_by_id(enrollment.course_id)
            section.independent_study_instructor_regid = (
                enrollment.instructor_reg_id)

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
                enrollment.section.is_withdrawn = True

            # Add or remove independent study course
            self.data.add(CourseCSV(section=enrollment.section))

        elif len(enrollment.section.linked_section_urls):
            # Add/remove primary instructor for each linked section
            for url in enrollment.section.linked_section_urls:
                try:
                    linked_section = get_section_by_url(url)
                    self.data.add(SectionCSV(section=linked_section))
                    self.add_teacher_enrollment_data(linked_section,
                                                     enrollment.person,
                                                     enrollment.status)
                except DataFailureException as err:
                    continue

        else:
            self.data.add(SectionCSV(section=enrollment.section))
            self.add_teacher_enrollment_data(
                enrollment.section, enrollment.person, enrollment.status)

    def _process_student_enrollment(self, enrollment):
        registration = Registration(section=enrollment.section,
                                    person=enrollment.person,
                                    is_active=enrollment.is_active())
        self.add_student_enrollment_data(registration)
        self.data.add(SectionCSV(section=enrollment.section))

    def _requeue_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = PRIORITY_DEFAULT
        enrollment.save()
        self.logger.info("Requeue enrollment %s in %s: %s" % (
            enrollment.reg_id, enrollment.course_id, err))

    def _skip_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = PRIORITY_NONE
        enrollment.save()
        logger.info("Skip enrollment %s in %s: %s" % (
            enrollment.reg_id, enrollment.course_id, err))

    def _init_build(self, **kwargs):
        now = datetime.utcnow().replace(tzinfo=utc)
        timeout = getattr(settings, 'MISSING_LOGIN_ID_RETRY_TIMEOUT', 48)
        self.retry_missing_id = now - timedelta(hours=timeout)
