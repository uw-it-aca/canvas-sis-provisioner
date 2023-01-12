# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from uw_sws.models import Term, Section
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
from restclients_core.exceptions import DataFailureException
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao.course import *
from datetime import datetime
import mock


@fdao_sws_override
@fdao_pws_override
class SectionPolicyTest(TestCase):
    def test_valid_canvas_course_id(self):
        self.assertEquals(valid_canvas_course_id('12345'), None)
        self.assertEquals(valid_canvas_course_id('0'), None)
        self.assertEquals(valid_canvas_course_id('1111111111'), None)
        self.assertRaises(
            CoursePolicyException, valid_canvas_course_id, None)
        self.assertRaises(
            CoursePolicyException, valid_canvas_course_id, 'abc')
        self.assertRaises(
            CoursePolicyException, valid_canvas_course_id, '1234z')

    def test_valid_course_sis_id(self):
        self.assertEquals(valid_course_sis_id('12345'), None)
        self.assertEquals(valid_course_sis_id('abc'), None)
        self.assertEquals(valid_course_sis_id('0'), None)
        self.assertRaises(CoursePolicyException, valid_course_sis_id, None)
        self.assertRaises(CoursePolicyException, valid_course_sis_id, '')

    def test_valid_adhoc_course_sis_id(self):
        self.assertEquals(valid_adhoc_course_sis_id('course_12345'), None)
        self.assertEquals(valid_adhoc_course_sis_id('course_1'), None)
        self.assertRaises(
            CoursePolicyException, valid_adhoc_course_sis_id, None)
        self.assertRaises(
            CoursePolicyException, valid_adhoc_course_sis_id, '0')
        self.assertRaises(
            CoursePolicyException, valid_adhoc_course_sis_id, '')
        self.assertRaises(
            CoursePolicyException, valid_adhoc_course_sis_id, 'abc')

    def test_valid_academic_course_sis_id(self):
        self.assertEquals(
            valid_academic_course_sis_id('2016-autumn-ABC-100-A'), None)
        self.assertEquals(
            valid_academic_course_sis_id('2016-autumn-ABC-100-AA'), None)
        self.assertEquals(
            valid_academic_course_sis_id('2016-autumn-ABC-100-A2'), None)
        self.assertEquals(
            valid_academic_course_sis_id('2016-autumn-AB&C-100-A'), None)
        self.assertEquals(
            valid_academic_course_sis_id('2016-autumn-A B-100-A'), None)
        self.assertEquals(
            valid_academic_course_sis_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'),
            None)

        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id, None)
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id, '0')
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id, '')
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id, 'abc')
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id,
            '2016-autumn-abc-100-a')

        # invalid instructor reg_ids
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id,
            '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF123456789')
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id,
            '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF12345678901')
        self.assertRaises(
            CoursePolicyException, valid_academic_course_sis_id,
            '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF123456789Z')

    def test_valid_academic_section_sis_id(self):
        self.assertEquals(
            valid_academic_section_sis_id('2016-autumn-ABC-100-AA'), None)
        self.assertEquals(
            valid_academic_section_sis_id('2016-autumn-ABC-100-A--'), None)
        self.assertEquals(
            valid_academic_section_sis_id('2016-autumn-ABC-100-A2'), None)
        self.assertEquals(
            valid_academic_section_sis_id('2016-autumn-AB&C-100-AA'), None)
        self.assertEquals(
            valid_academic_section_sis_id('2016-autumn-A B-100-AA'), None)
        self.assertEquals(
            valid_academic_section_sis_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'),
            None)

        self.assertRaises(
            CoursePolicyException, valid_academic_section_sis_id, None)
        self.assertRaises(
            CoursePolicyException, valid_academic_section_sis_id, '0')
        self.assertRaises(
            CoursePolicyException, valid_academic_section_sis_id, '')
        self.assertRaises(
            CoursePolicyException, valid_academic_section_sis_id, 'abc')
        self.assertRaises(
            CoursePolicyException, valid_academic_section_sis_id,
            '2016-autumn-ABC-100-ABC')

    def test_adhoc_course_sis_id(self):
        self.assertEquals(adhoc_course_sis_id('12345'), 'course_12345')
        self.assertEquals(adhoc_course_sis_id('0'), 'course_0')
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, None)
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, 'abc')
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, '')

    def test_group_section_sis_id(self):
        self.assertEquals(
            group_section_sis_id('2016-autumn-ABC-100-A'),
            '2016-autumn-ABC-100-A-groups')
        self.assertEquals(
            group_section_sis_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'),
            '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890-groups')

    @override_settings(DEFAULT_GROUP_SECTION_NAME='GROUP_NAME')
    def test_group_section_name(self):
        self.assertEquals(group_section_name(), 'GROUP_NAME')

    def test_section_id_from_url(self):
        self.assertEquals(
            section_id_from_url(
                '/student/v5/course/2016,autumn,ABC,100/A.json'),
            '2016-autumn-ABC-100-A')
        self.assertEquals(
            section_id_from_url(
                '/student/v5/course/2016,autumn,ABC,100/AB.json'),
            '2016-autumn-ABC-100-AB')
        self.assertEquals(
            section_id_from_url(
                '/student/v5/course/2016,autumn,A%20B%20C,100/AB.json'),
            '2016-autumn-A B C-100-AB')
        self.assertEquals(
            section_id_from_url(
                '/student/v5/course/2016,autumn,AB%26C,100/AB.json'),
            '2016-autumn-AB&C-100-AB')
        self.assertEquals(section_id_from_url(''), None)
        self.assertEquals(section_id_from_url(None), None)

    def test_section_label_from_section_id(self):
        self.assertEquals(
            section_label_from_section_id('2016-autumn-ABC-100-A'),
            '2016,autumn,ABC,100/A')
        self.assertEquals(
            section_label_from_section_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'),
            '2016,autumn,ABC,100/A')
        self.assertEquals(
            section_label_from_section_id('2016-autumn-ABC-100-AB'),
            '2016,autumn,ABC,100/AB')
        self.assertEquals(
            section_label_from_section_id('2016-autumn-ABC-100-A--'),
            '2016,autumn,ABC,100/A')
        self.assertEquals(
            section_label_from_section_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'),
            '2016,autumn,ABC,100/A')

        self.assertRaises(
            CoursePolicyException, section_label_from_section_id,
            '2016-autumn-ABC-100')
        self.assertRaises(
            CoursePolicyException, section_label_from_section_id, '')
        self.assertRaises(
            CoursePolicyException, section_label_from_section_id, None)

    def test_instructor_regid_from_section_id(self):
        self.assertEquals(
            instructor_regid_from_section_id('2016-autumn-ABC-100-A'), None)
        self.assertEquals(
            instructor_regid_from_section_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'),
            'ABCDEF1234567890ABCDEF1234567890')
        self.assertEquals(
            instructor_regid_from_section_id('2016-autumn-ABC-100-A--'), None)
        self.assertEquals(
            instructor_regid_from_section_id(
                '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'),
            'ABCDEF1234567890ABCDEF1234567890')
        self.assertEquals(
            instructor_regid_from_section_id('2016-autumn-ABC-100'), None)
        self.assertEquals(instructor_regid_from_section_id(''), None)
        self.assertEquals(instructor_regid_from_section_id(None), None)

    def test_valid_canvas_section(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        section.primary_lms = None
        self.assertEquals(valid_canvas_section(section), None)

        section.primary_lms = Section.LMS_CANVAS
        self.assertEquals(valid_canvas_section(section), None)

        section.primary_lms = 'ABC'
        self.assertRaises(CoursePolicyException, valid_canvas_section, section)

        section.primary_lms = Section.LMS_CANVAS
        section.delete_flag = Section.DELETE_FLAG_ACTIVE
        self.assertEquals(is_active_section(section), True)

        section.delete_flag = Section.DELETE_FLAG_WITHDRAWN
        self.assertEquals(is_active_section(section), False)

        section.primary_lms = 'ABC'
        section.delete_flag = Section.DELETE_FLAG_ACTIVE
        self.assertEquals(is_active_section(section), False)

    def test_suspended_canvas_section(self):
        section = get_section_by_label('2013,winter,BIGDATA,220/A')
        self.assertEquals(section.is_active(), False)
        self.assertEquals(section.is_withdrawn(), False)
        self.assertEquals(section.is_suspended(), True)
        self.assertEquals(is_active_section(section), True)

    def test_section_short_name(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')
        self.assertEquals(section_short_name(section), 'TRAIN 101 A')

    def test_section_long_name(self):
        section = get_section_by_id('2013-spring-TRAIN-101-A')
        self.assertEquals(
            section_long_name(section), 'TRAIN 101 A Sp 13: Intro Train')

        section.course_title_long = ''
        self.assertEquals(section_long_name(section), 'TRAIN 101 A Sp 13')

        section.course_title_long = 'Intro Train'
        section.is_independent_start = True
        self.assertEquals(
            section_long_name(section), 'TRAIN 101 A Sp 13: Intro Train')

        section.course_title_long = ''
        self.assertEquals(section_long_name(section), 'TRAIN 101 A Sp 13')

    def test_independent_study_section_long_name(self):
        section = get_section_by_id(
            '2013-autumn-REHAB-591-C-8BD26A286A7D11D5A4AE0004AC494FFE')
        self.assertEquals(
            section_long_name(section),
            'REHAB 591 C Au 13: Graduate Project (Bill Teacher)')

        section.course_title_long = None
        self.assertEquals(
            section_long_name(section), 'REHAB 591 C Au 13 (Bill Teacher)')

        section.course_title_long = ''
        self.assertEquals(
            section_long_name(section), 'REHAB 591 C Au 13 (Bill Teacher)')


@fdao_sws_override
@fdao_pws_override
class SectionByIDTest(TestCase):
    def test_section_by_id(self):
        section = get_section_by_id('2013-summer-TRAIN-101-A')
        self.assertEquals(section.section_label(), '2013,summer,TRAIN,101/A')

    def test_independent_study_section_by_id(self):
        section = get_section_by_id(
            '2013-autumn-REHAB-591-C-8BD26A286A7D11D5A4AE0004AC494FFE')
        self.assertEquals(section.section_label(), '2013,autumn,REHAB,591/C')
        self.assertEquals(
            section.independent_study_instructor_regid,
            '8BD26A286A7D11D5A4AE0004AC494FFE')


@fdao_sws_override
@fdao_pws_override
class XlistSectionTest(TestCase):
    def test_canvas_xlist_id(self):
        section = get_section_by_id('2013-summer-TRAIN-101-A')
        self.assertEquals(
            canvas_xlist_id([section]), '2013-summer-TRAIN-101-A')

        section.delete_flag = Section.DELETE_FLAG_WITHDRAWN
        self.assertEquals(canvas_xlist_id([section]), None)

        section1 = get_section_by_id('2013-spring-TRAIN-101-A')
        section2 = get_section_by_id('2013-summer-TRAIN-101-A')

        self.assertEquals(
            canvas_xlist_id([section1, section2]), '2013-spring-TRAIN-101-A')

        section2.lms_ownership = Section.LMS_OWNER_OL
        self.assertEquals(
            canvas_xlist_id([section1, section2]), '2013-summer-TRAIN-101-A')


@fdao_sws_override
@fdao_pws_override
class NewSectionQueryTest(TestCase):
    @mock.patch('sis_provisioner.dao.course.get_changed_sections_by_term')
    def test_changed_sections_by_term(self, mock_fn):
        r = get_new_sections_by_term('2013-12-12', 'abc')
        mock_fn.assert_called_with(
            '2013-12-12', 'abc',
            delete_flag=[Section.DELETE_FLAG_ACTIVE,
                         Section.DELETE_FLAG_SUSPENDED],
            future_terms=0, include_secondaries='on',
            transcriptable_course='all')

    def test_new_sections_by_term(self):
        changed_date = datetime(2013, 12, 12).date()
        term = Term(quarter="winter", year=2013)
        existing = {}

        # 404, no resource
        self.assertRaises(
            DataFailureException, get_new_sections_by_term, changed_date, term)


@fdao_sws_override
@fdao_pws_override
class RegistrationsBySectionTest(TestCase):
    def test_get_registrations_by_section(self):
        section = get_section_by_label('2013,winter,DROP_T,100/B')
        registrations = get_registrations_by_section(section)

        self.assertEquals(len(registrations), 2)


@fdao_sws_override
@fdao_pws_override
class TimeScheduleConstructionTest(TestCase):
    def test_by_campus(self):
        time_schedule_constructions = {
            'seattle': False, 'tacoma': True, 'bothell': False}
        time_schedule_published = {
            'seattle': False, 'tacoma': False, 'bothell': False}

        term = Term(year=2013, quarter='summer')
        term.time_schedule_construction = time_schedule_constructions
        term.time_schedule_published = time_schedule_published
        section = Section(term=term)

        section.course_campus = 'Seattle'
        self.assertTrue(is_time_schedule_ready(section), 'Seattle')

        section.course_campus = 'Tacoma'
        self.assertFalse(is_time_schedule_ready(section), 'Tacoma')

        section.course_campus = 'Bothell'
        self.assertFalse(is_time_schedule_ready(section), 'Bothell')

        section.course_campus = 'PCE'
        self.assertTrue(is_time_schedule_ready(section), 'PCE')
