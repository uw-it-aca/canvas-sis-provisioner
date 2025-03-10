# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from sis_provisioner.dao.term import *
from sis_provisioner.dao.course import get_section_by_label
from uw_sws.util import fdao_sws_override
from uw_pws.util import fdao_pws_override
from datetime import datetime


@fdao_sws_override
@fdao_pws_override
class ActiveTermTest(TestCase):
    def test_current_active_term(self):
        self.assertEqual(
            get_current_active_term(datetime(2013, 7, 15)).term_label(),
            '2013,summer')
        self.assertEqual(
            get_current_active_term(
                datetime(2013, 8, 27, hour=15)).term_label(),
            '2013,summer')
        self.assertEqual(
            get_current_active_term(
                datetime(2013, 8, 27, hour=19)).term_label(),
            '2013,autumn')

    def test_all_active_terms(self):
        terms = get_all_active_terms(datetime(2013, 7, 15))
        self.assertEqual(terms[0].term_label(), '2013,summer')
        self.assertEqual(terms[1].term_label(), '2013,autumn')
        self.assertEqual(terms[2].term_label(), '2014,winter')

        terms = get_all_active_terms(datetime(2013, 8, 28))
        self.assertEqual(terms[0].term_label(), '2013,autumn')
        self.assertEqual(terms[1].term_label(), '2014,winter')
        self.assertEqual(terms[2].term_label(), '2014,spring')

    def test_is_active_term(self):
        term = get_current_active_term(datetime(2013, 7, 15))
        self.assertTrue(is_active_term(term, dt=datetime(2013, 7, 15)))
        self.assertFalse(is_active_term(term, dt=datetime(2013, 8, 28)))


@fdao_sws_override
@fdao_pws_override
class TermPolicyTest(TestCase):
    @override_settings(UWEO_INDIVIDUAL_START_TERM_SIS_ID='test-id')
    def test_term_sis_id(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        self.assertEqual(term_sis_id(section), '2013-spring')

        section.is_independent_start = True
        self.assertEqual(term_sis_id(section), 'test-id')

    @override_settings(UWEO_INDIVIDUAL_START_TERM_NAME='Individual Start')
    def test_term_name(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        self.assertEqual(term_name(section), 'Spring 2013')

        section.is_independent_start = True
        self.assertEqual(term_name(section), 'Individual Start')

    def test_term_start_date(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')

        self.assertEqual(
            str(quarter_term_start_date(section.term)), '2013-06-24')

        section.is_independent_start = False
        self.assertEqual(term_start_date(section), '2013-06-24T00:00:00-0800')

        section.is_independent_start = True
        self.assertEqual(term_start_date(section), None)

    def test_term_end_date(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')

        self.assertEqual(
            str(quarter_term_end_date(section.term)), '2013-08-28')

        section.is_independent_start = False
        self.assertEqual(term_end_date(section), '2013-08-28T00:00:00-0800')

        section.is_independent_start = True
        self.assertEqual(term_end_date(section), None)

    def test_term_overrides(self):
        term = get_term_by_year_and_quarter(2013, 'summer')
        self.maxDiff = None
        self.assertEqual(term_date_overrides(term), {
            'StudentEnrollment': {'start_at': '2012-06-24T00:00:00-0800'},
            'TaEnrollment': {'end_at': '2020-08-26T00:00:00-0800'},
            'TeacherEnrollment': {'end_at': '2020-08-26T00:00:00-0800'},
            'DesignerEnrollment': {'end_at': '2020-08-26T00:00:00-0800'},
        })

    @override_settings(
        EXTENDED_COURSE_END_DATE_SUBACCOUNTS={'sis_root:abc': 5})
    def test_course_end_date(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')
        self.assertEqual(
            course_end_date(section, 'sis_root:abc:xyz'),
            '2013-09-02T00:00:00-0800')

        self.assertEqual(course_end_date(section, 'sis_root:def'), None)
