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
    def __init__(self, enrollments):
        super(Builder, self).__init__()
        self.enrollments = enrollments

    def _process_enrollment(self, enrollment):
        try:
            person = get_person_by_regid(enrollment.reg_id)

            section = self.get_section_resource_by_id(enrollment.course_id)
            section.independent_study_instructor_regid = (
                enrollment.instructor_reg_id)

            if not is_active_section(section):
                return

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
            if section.is_independent_study:
                # Add or remove independent study course
                if not enrollment.is_active():
                    section.is_withdrawn = True

                self.data.add(CourseCSV(section=section))

                if enrollment.is_active():
                    self.data.add(SectionCSV(section=section))
                    self.add_teacher_enrollment_data(section, person,
                                                     enrollment.status)

            elif len(section.linked_section_urls):
                # Add/remove primary instructor for each linked section
                for url in section.linked_section_urls:
                    try:
                        linked_section = get_section_by_url(url)
                    except Exception as err:
                        continue

                    self.data.add(SectionCSV(section=linked_section))
                    self.add_teacher_enrollment_data(linked_section, person,
                                                     enrollment.status)

            else:
                self.data.add(SectionCSV(section=section))
                self.add_teacher_enrollment_data(section, person,
                                                 enrollment.status)

        else:  # student/auditor
            if len(section.linked_section_urls):
                # Don't enroll students into primary sections
                self._skip_enrollment_event(
                    enrollment, 'Section has linked sections')
                return

            registration = Registration(section=section, person=person,
                                        is_active=enrollment.is_active())

            self.data.add(SectionCSV(section=section))
            self.add_student_enrollment_data(registration)

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

    def build(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        timeout = getattr(settings, 'MISSING_LOGIN_ID_RETRY_TIMEOUT', 48)
        self.retry_missing_id = now - timedelta(hours=timeout)

        for enrollment in self.enrollments:
            self._process_enrollment(enrollment)

        return self.write()
