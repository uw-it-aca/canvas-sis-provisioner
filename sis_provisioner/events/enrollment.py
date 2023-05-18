# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.events import SISProvisionerProcessor
from sis_provisioner.models.events import EnrollmentLog
from sis_provisioner.dao.canvas import (
    get_student_sis_import_role, ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.dao.user import valid_reg_id
from sis_provisioner.exceptions import (
    InvalidLoginIdException, UnhandledActionCodeException)
from uw_sws.models import Term, Section
from dateutil.parser import parse as date_parse

log_prefix = 'ENROLLMENT:'
QUEUE_SETTINGS_NAME = 'ENROLLMENT_V2'
STATUS_CODES = {
    'A': ENROLLMENT_ACTIVE, 'D': ENROLLMENT_DELETED, 'S': ENROLLMENT_ACTIVE}


class EnrollmentProcessor(SISProvisionerProcessor):
    """
    Collects enrollment event described by
    https://wiki.cac.washington.edu/display/StudentEvents/UW+Course+Enrollment+v2
    """
    _logModel = EnrollmentLog

    # What we expect in a v2 enrollment message
    _eventMessageType = 'uw-student-registration-v2'
    _eventMessageVersion = '2'

    def __init__(self):
        super(EnrollmentProcessor, self).__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME, is_encrypted=True)

    def process_message_body(self, json_data):
        enrollments = []
        for event in json_data.get('Events', []):
            section_data = event['Section']
            course_data = section_data['Course']

            section = Section()
            section.term = Term(quarter=course_data['Quarter'],
                                year=course_data['Year'])
            section.curriculum_abbr = course_data['CurriculumAbbreviation']
            section.course_number = course_data['CourseNumber']
            section.section_id = section_data['SectionID']
            section.is_primary_section = True
            section.linked_section_urls = []

            if ('PrimarySection' in event and
                    'Course' in event['PrimarySection']):
                primary_course = event['PrimarySection']['Course']
                if primary_course:
                    section.is_primary_section = False
                    section.primary_section_curriculum_abbr = (
                        primary_course['CurriculumAbbreviation'])
                    section.primary_section_course_number = (
                        primary_course['CourseNumber'])
                    section.primary_section_id = (
                        event['PrimarySection']['SectionID'])

            try:
                valid_reg_id(event['Person']['UWRegID'])
                data = {
                    'Section': section,
                    'Role': get_student_sis_import_role(),
                    'UWRegID': event['Person']['UWRegID'],
                    'Status': self._enrollment_status(event),
                    'LastModified': date_parse(event['LastModified']),
                    'DuplicateCode': event['DuplicateEnrollmentCode'],
                    'InstructorUWRegID': event['Instructor']['UWRegID'] if (
                        'Instructor' in event and event['Instructor'] and
                        'UWRegID' in event['Instructor']) else None
                }

                if 'Auditor' in event and event['Auditor']:
                    data['Role'] = 'Auditor'

                if 'RequestDate' in event:
                    data['RequestDate'] = date_parse(event['RequestDate'])

                enrollments.append(data)
                outcome = 'ACCEPT'
            except UnhandledActionCodeException:
                outcome = 'IGNORE CODE'
            except InvalidLoginIdException:
                outcome = 'INVALID REGID'

            self._log(event, section, outcome)

        self.load_enrollments(enrollments)

    def _enrollment_status(self, event):
        action_code = event['Action']['Code'].upper()
        if action_code not in STATUS_CODES:
            raise UnhandledActionCodeException()
        return STATUS_CODES[action_code]

    def _log(self, event, section, outcome):
        self.logger.info((
            '{} {} code: {}, regid: {}, section: {}, duplicate_code: {}, '
            'last_modified: {}, event_id: {}').format(
                log_prefix,
                outcome,
                event['Action']['Code'],
                event['Person']['UWRegID'],
                section.canvas_section_sis_id(),
                event['DuplicateEnrollmentCode'],
                event['LastModified'],
                event['EventID']))
