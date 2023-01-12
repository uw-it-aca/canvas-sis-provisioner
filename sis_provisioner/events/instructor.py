# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.events import SISProvisionerProcessor
from sis_provisioner.dao.canvas import (
    get_instructor_sis_import_role, ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.dao.course import is_time_schedule_ready
from sis_provisioner.dao.term import (
    get_term_by_year_and_quarter, is_active_term)
from sis_provisioner.models.events import InstructorLog
from restclients_core.exceptions import DataFailureException
from uw_sws.models import Section
from dateutil.parser import parse as date_parse

log_prefix = 'INSTRUCTOR:'
QUEUE_SETTINGS_NAME_ADD = 'INSTRUCTOR_ADD'
QUEUE_SETTINGS_NAME_DROP = 'INSTRUCTOR_DROP'


class InstructorProcessor(SISProvisionerProcessor):
    _logModel = InstructorLog

    def process_message_body(self, json_data):
        self._previous_instructors = self._instructors_from_section_json(
            json_data['Previous'])
        self._current_instructors = self._instructors_from_section_json(
            json_data['Current'])
        self._last_modified = date_parse(json_data['EventDate'])

        section_data = json_data['Current']
        if not section_data:
            section_data = json_data['Previous']

        course_data = section_data['Course']

        try:
            term = get_term_by_year_and_quarter(
                section_data['Term']['Year'], section_data['Term']['Quarter'])
        except DataFailureException as err:
            self.logger.info('{} ERROR get term: {}'.format(log_prefix, err))
            return

        if not is_active_term(term):
            self.logger.info(
                '{} IGNORE Inactive section {}-{}-{}-{}'.format(
                    log_prefix, term.canvas_sis_id(),
                    course_data['CurriculumAbbreviation'],
                    course_data['CourseNumber'], section_data['SectionID']))
            return

        section = Section(
            term=term,
            course_campus=section_data['CourseCampus'],
            curriculum_abbr=course_data['CurriculumAbbreviation'],
            course_number=course_data['CourseNumber'],
            section_id=section_data['SectionID'],
            is_independent_study=section_data['IndependentStudy'])

        if not is_time_schedule_ready(section):
            self._log_tsc_ignore(section.canvas_section_sis_id())
            return

        sections = []
        primary_section = section_data["PrimarySection"]
        if (primary_section is not None and
                primary_section["SectionID"] != section.section_id):
            section.is_primary_section = False
            self._set_primary_section(section, primary_section)
            sections.append(section)
        else:
            if len(section_data["LinkedSectionTypes"]):
                for linked_section_type in section_data["LinkedSectionTypes"]:
                    for linked_section_data in (
                            linked_section_type["LinkedSections"]):
                        lsd_data = linked_section_data['Section']
                        section = Section(
                            term=term,
                            curriculum_abbr=lsd_data['CurriculumAbbreviation'],
                            course_number=lsd_data['CourseNumber'],
                            section_id=lsd_data['SectionID'],
                            is_primary_section=False,
                            is_independent_study=section_data[
                                'IndependentStudy'])
                        self._set_primary_section(section, primary_section)
                        sections.append(section)
            else:
                section.is_primary_section = True
                sections.append(section)

        for section in sections:
            self.load_instructors(section)

    def _set_primary_section(self, section, primary_section):
        if primary_section is not None:
            section.primary_section_curriculum_abbr = (
                primary_section['CurriculumAbbreviation'])
            section.primary_section_course_number = (
                primary_section['CourseNumber'])
            section.primary_section_id = primary_section['SectionID']

    def enrollments(self, reg_id_list, status, section):
        enrollments = []
        enrollment_data = {
            'Section': section,
            'Role': get_instructor_sis_import_role(),
            'Status': status,
            'LastModified': self._last_modified,
            'InstructorUWRegID': None
        }

        for reg_id in reg_id_list:
            enrollment_data['UWRegID'] = reg_id
            enrollment_data['InstructorUWRegID'] = reg_id if (
                section.is_independent_study) else None

            enrollments.append(enrollment_data)

        return enrollments

    def load_instructors(self, section):
        raise Exception('No load_instructors method')

    def _instructors_from_section_json(self, section):
        instructors = {}
        if section:
            for meeting in section['Meetings']:
                for instructor in meeting['Instructors']:
                    if instructor['Person']['RegID']:
                        instructors[instructor['Person']['RegID']] = instructor
                    else:
                        person = []
                        for k, v in instructor['Person'].items():
                            person.append('[{}] = "{}"'.format(k, v))

                        course_data = section['Course']
                        self.logger.info(
                            '{} IGNORE missing regid for {}-{}-{}: {}'.format(
                                log_prefix,
                                course_data['CurriculumAbbreviation'],
                                course_data['CourseNumber'],
                                section['SectionID'],
                                ', '.join(person)))

        return instructors.keys()


class InstructorAddProcessor(InstructorProcessor):
    """
    UW Course Instructor Add Event Handler
    """

    # What we expect in an instructor add message
    _eventMessageType = 'uw-instructor-add'
    _eventMessageVersion = '1'

    def __init__(self):
        super(InstructorAddProcessor, self).__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME_ADD, is_encrypted=False)

    def load_instructors(self, section):
        add = [reg_id for reg_id in self._current_instructors
               if reg_id not in self._previous_instructors]
        enrollments = self.enrollments(add, ENROLLMENT_ACTIVE, section)
        self.load_enrollments(enrollments)

    def _log_tsc_ignore(self, section_id):
        self.logger.info('{} IGNORE add: TS not ready for {}'.format(
            log_prefix, section_id))


class InstructorDropProcessor(InstructorProcessor):
    """
    UW Course Instructor Drop Event Handler
    """

    # What we expect in an instructor drop message
    _eventMessageType = 'uw-instructor-drop'
    _eventMessageVersion = '1'

    def __init__(self):
        super(InstructorDropProcessor, self).__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME_DROP, is_encrypted=False)

    def load_instructors(self, section):
        drop = [reg_id for reg_id in self._previous_instructors
                if reg_id not in self._current_instructors]
        enrollments = self.enrollments(drop, ENROLLMENT_DELETED, section)
        self.load_enrollments(enrollments)

    def _log_tsc_ignore(self, section_id):
        self.logger.info("{} IGNORE drop: TS not ready for {}".format(
            log_prefix, section_id))
