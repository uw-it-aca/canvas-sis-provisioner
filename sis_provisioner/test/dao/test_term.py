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
        self.assertEquals(
            get_current_active_term(datetime(2013, 7, 15)).term_label(),
            '2013,summer')
        self.assertEquals(
            get_current_active_term(
                datetime(2013, 8, 27, hour=15)).term_label(),
            '2013,summer')
        self.assertEquals(
            get_current_active_term(
                datetime(2013, 8, 27, hour=19)).term_label(),
            '2013,autumn')

    def test_all_active_terms(self):
        terms = get_all_active_terms(datetime(2013, 7, 15))
        self.assertEquals(terms[0].term_label(), '2013,summer')
        self.assertEquals(terms[1].term_label(), '2013,autumn')
        self.assertEquals(terms[2].term_label(), '2014,winter')

        terms = get_all_active_terms(datetime(2013, 8, 28))
        self.assertEquals(terms[0].term_label(), '2013,autumn')
        self.assertEquals(terms[1].term_label(), '2014,winter')
        self.assertEquals(terms[2].term_label(), '2014,spring')

    def test_is_active_term(self):
        term = get_current_active_term(datetime(2013, 7, 15))
        self.assertEquals(is_active_term(term, dt=datetime(2013, 7, 15)),
                          True)
        self.assertEquals(is_active_term(term, dt=datetime(2013, 8, 28)),
                          False)


@fdao_sws_override
@fdao_pws_override
class TermPolicyTest(TestCase):
    @override_settings(UWEO_INDIVIDUAL_START_TERM_SIS_ID='test-id')
    def test_term_sis_id(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        self.assertEquals(term_sis_id(section), '2013-spring')

        section.is_independent_start = True
        self.assertEquals(term_sis_id(section), 'test-id')

    @override_settings(UWEO_INDIVIDUAL_START_TERM_NAME='Individual Start')
    def test_term_name(self):
        section = get_section_by_label('2013,spring,TRAIN,101/A')

        self.assertEquals(term_name(section), 'Spring 2013')

        section.is_independent_start = True
        self.assertEquals(term_name(section), 'Individual Start')

    def test_term_start_date(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')

        self.assertEquals(
            str(quarter_term_start_date(section.term)), '2013-06-24')

        section.is_independent_start = False
        self.assertEquals(term_start_date(section), '2013-06-24T00:00:00-0800')

        section.is_independent_start = True
        self.assertEquals(term_start_date(section), None)

    def test_term_end_date(self):
        section = get_section_by_label('2013,summer,TRAIN,101/A')

        self.assertEquals(
            str(quarter_term_end_date(section.term)), '2013-08-28')

        section.is_independent_start = False
        self.assertEquals(term_end_date(section), '2013-08-28T00:00:00-0800')

        section.is_independent_start = True
        self.assertEquals(term_end_date(section), None)

    def test_term_overrides(self):
        term = get_term_by_year_and_quarter(2013, 'summer')
        self.assertEquals(term_date_overrides(term), {
            'StudentEnrollment': (
                '2012-06-24T00:00:00-0800', '2014-08-28T00:00:00-0800'),
            'TaEnrollment': (
                '2012-06-24T00:00:00-0800', '2014-08-28T00:00:00-0800'),
            'TeacherEnrollment': (
                '2012-06-24T00:00:00-0800', '2018-08-27T00:00:00-0800'),
            'DesignerEnrollment': (
                '2012-06-24T00:00:00-0800', '2014-08-28T00:00:00-0800')})
