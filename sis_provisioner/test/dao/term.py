from django.test import TestCase
from sis_provisioner.dao.term import *
from sis_provisioner.dao.course import get_section_by_label
from datetime import datetime


class ActiveTermTest(TestCase):
    def test_current_active_term(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File'):

           self.assertEquals(get_current_active_term(datetime(2013, 7, 15)).term_label(),
                             '2013,summer')
           self.assertEquals(get_current_active_term(datetime(2013, 8, 27, hour=15)).term_label(),
                             '2013,summer')
           self.assertEquals(get_current_active_term(datetime(2013, 8, 27, hour=19)).term_label(),
                             '2013,autumn')

    def test_all_active_terms(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File'):
           
            terms = get_all_active_terms(datetime(2013, 7, 15))
            self.assertEquals(terms[0].term_label(), '2013,summer')
            self.assertEquals(terms[1].term_label(), '2013,autumn')
            self.assertEquals(terms[2].term_label(), '2014,winter')

            terms = get_all_active_terms(datetime(2013, 8, 28))
            self.assertEquals(terms[0].term_label(), '2013,autumn')
            self.assertEquals(terms[1].term_label(), '2014,winter')
            self.assertEquals(terms[2].term_label(), '2014,spring')


class TermPolicyTest(TestCase):
    def test_term_sis_id(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File',
                UWEO_INDIVIDUAL_START_TERM_SIS_ID='test-id'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            self.assertEquals(term_sis_id(section), '2013-spring')

            section.is_independent_start = True
            self.assertEquals(term_sis_id(section), 'test-id')

    def test_term_name(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File',
                UWEO_INDIVIDUAL_START_TERM_NAME='Individual Start'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            self.assertEquals(term_name(section), 'Spring 2013')

            section.is_independent_start = True
            self.assertEquals(term_name(section), 'Individual Start')

    def test_term_start_date(self):
         with self.settings(
                 RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                 RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

             section = get_section_by_label('2013,summer,TRAIN,101/A')

             section.is_independent_start = False
             self.assertEquals(term_start_date(section), '2013-06-24T00:00:00-0800')

             section.is_independent_start = True
             self.assertEquals(term_start_date(section), None)

    def test_term_end_date(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,summer,TRAIN,101/A')

            section.is_independent_start = False
            self.assertEquals(term_end_date(section), '2013-08-28T00:00:00-0800')

            section.is_independent_start = True
            self.assertEquals(term_end_date(section), None)
