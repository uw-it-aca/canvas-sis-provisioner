from django.test import TestCase
from django.conf import settings
from restclients.models.sws import Term, Section, TimeScheduleConstruction
from sis_provisioner.exceptions import CoursePolicyException
from sis_provisioner.dao.course import *


class SectionPolicyTest(TestCase):
    def test_valid_canvas_course_id(self):
        self.assertEquals(valid_canvas_course_id(12345), None)
        self.assertEquals(valid_canvas_course_id('12345'), None)
        self.assertEquals(valid_canvas_course_id(0), None)
        self.assertEquals(valid_canvas_course_id(1111111111), None)
        self.assertRaises(CoursePolicyException, valid_canvas_course_id, None)
        self.assertRaises(CoursePolicyException, valid_canvas_course_id, 'abc')
        self.assertRaises(CoursePolicyException, valid_canvas_course_id, '1234z')

    def test_valid_course_sis_id(self):
        self.assertEquals(valid_course_sis_id(12345), None)
        self.assertEquals(valid_course_sis_id('abc'), None)
        self.assertEquals(valid_course_sis_id('0'), None)
        self.assertRaises(CoursePolicyException, valid_course_sis_id, None)
        self.assertRaises(CoursePolicyException, valid_course_sis_id, 0)
        self.assertRaises(CoursePolicyException, valid_course_sis_id, '')

    def test_valid_adhoc_course_sis_id(self):
        self.assertEquals(valid_adhoc_course_sis_id('course_12345'), None)
        self.assertEquals(valid_adhoc_course_sis_id('course_1'), None)
        self.assertRaises(CoursePolicyException, valid_adhoc_course_sis_id, None)
        self.assertRaises(CoursePolicyException, valid_adhoc_course_sis_id, 0)
        self.assertRaises(CoursePolicyException, valid_adhoc_course_sis_id, '')
        self.assertRaises(CoursePolicyException, valid_adhoc_course_sis_id, 'abc')

    def test_valid_academic_course_sis_id(self):
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-ABC-100-A'), None)
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-ABC-100-AA'), None)
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-ABC-100-A2'), None)
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-AB&C-100-A'), None)
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-A B-100-A'), None)
        self.assertEquals(valid_academic_course_sis_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'), None)
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, None)
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, 0)
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, '')
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, 'abc')
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, '2016-autumn-abc-100-a')

        # invalid instructor reg_ids
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF123456789')
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF12345678901')
        self.assertRaises(CoursePolicyException, valid_academic_course_sis_id, '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF123456789Z')

    def test_valid_academic_section_sis_id(self):
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-ABC-100-AA'), None)
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-ABC-100-A--'), None)
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-ABC-100-A2'), None)
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-AB&C-100-AA'), None)
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-A B-100-AA'), None)
        self.assertEquals(valid_academic_section_sis_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'), None)
        self.assertRaises(CoursePolicyException, valid_academic_section_sis_id, None)
        self.assertRaises(CoursePolicyException, valid_academic_section_sis_id, 0)
        self.assertRaises(CoursePolicyException, valid_academic_section_sis_id, '')
        self.assertRaises(CoursePolicyException, valid_academic_section_sis_id, 'abc')
        self.assertRaises(CoursePolicyException, valid_academic_section_sis_id, '2016-autumn-ABC-100-ABC')

    def test_adhoc_course_sis_id(self):
        self.assertEquals(adhoc_course_sis_id('12345'), 'course_12345')
        self.assertEquals(adhoc_course_sis_id(12345), 'course_12345')
        self.assertEquals(adhoc_course_sis_id('0'), 'course_0')
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, None)
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, 'abc')
        self.assertRaises(CoursePolicyException, adhoc_course_sis_id, '')

    def test_group_section_sis_id(self):
        self.assertEquals(group_section_sis_id('2016-autumn-ABC-100-A'), '2016-autumn-ABC-100-A-groups')
        self.assertEquals(group_section_sis_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'), '2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890-groups')

    def test_group_section_name(self):
        with self.settings(DEFAULT_GROUP_SECTION_NAME='GROUP_NAME'):
            self.assertEquals(group_section_name(), 'GROUP_NAME')

    def test_section_label_from_section_id(self):
        self.assertEquals(section_label_from_section_id('2016-autumn-ABC-100-A'), '2016,autumn,ABC,100/A')
        self.assertEquals(section_label_from_section_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'), '2016,autumn,ABC,100/A')
        self.assertEquals(section_label_from_section_id('2016-autumn-ABC-100-AB'), '2016,autumn,ABC,100/AB')
        self.assertEquals(section_label_from_section_id('2016-autumn-ABC-100-A--'), '2016,autumn,ABC,100/A')
        self.assertEquals(section_label_from_section_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'), '2016,autumn,ABC,100/A')

        self.assertRaises(CoursePolicyException, section_label_from_section_id, '2016-autumn-ABC-100')
        self.assertRaises(CoursePolicyException, section_label_from_section_id, '')
        self.assertRaises(CoursePolicyException, section_label_from_section_id, None)

    def test_instructor_regid_from_section_id(self):
        self.assertEquals(instructor_regid_from_section_id('2016-autumn-ABC-100-A'), None)
        self.assertEquals(instructor_regid_from_section_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890'), 'ABCDEF1234567890ABCDEF1234567890')
        self.assertEquals(instructor_regid_from_section_id('2016-autumn-ABC-100-A--'), None)
        self.assertEquals(instructor_regid_from_section_id('2016-autumn-ABC-100-A-ABCDEF1234567890ABCDEF1234567890--'), 'ABCDEF1234567890ABCDEF1234567890')

        self.assertRaises(CoursePolicyException, instructor_regid_from_section_id, '2016-autumn-ABC-100')
        self.assertRaises(CoursePolicyException, instructor_regid_from_section_id, '')
        self.assertRaises(CoursePolicyException, instructor_regid_from_section_id, None)

    def test_valid_canvas_section(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            section.primary_lms = None
            self.assertEquals(valid_canvas_section(section), None)

            section.primary_lms = Section.LMS_CANVAS
            self.assertEquals(valid_canvas_section(section), None)

            section.primary_lms = 'ABC'
            self.assertRaises(CoursePolicyException, valid_canvas_section, section)

            section.primary_lms = Section.LMS_CANVAS
            section.is_withdrawn = False
            self.assertEquals(is_active_section(section), True)

            section.is_withdrawn = True
            self.assertEquals(is_active_section(section), False)

            section.primary_lms = 'ABC'
            section.is_withdrawn = False
            self.assertEquals(is_active_section(section), False)

    def test_section_short_name(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')
            self.assertEquals(section_short_name(section), 'TRAIN 101 A')

    def test_section_long_name(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_id('2013-spring-TRAIN-101-A')
            self.assertEquals(section_long_name(section), 'TRAIN 101 A: Intro Train')

    def test_independent_study_section_long_name(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_id('2013-autumn-REHAB-591-C-8BD26A286A7D11D5A4AE0004AC494FFE')
            self.assertEquals(section_long_name(section), 'REHAB 591 C: Graduate Project (Bill Teacher)')


class SectionByIDTest(TestCase):
    def test_section_by_id(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_id('2013-summer-TRAIN-101-A')

            self.assertEquals(section.section_label(), '2013,summer,TRAIN,101/A')

    def test_independent_study_section_by_id(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_id('2013-autumn-REHAB-591-C-8BD26A286A7D11D5A4AE0004AC494FFE')
            self.assertEquals(section.section_label(), '2013,autumn,REHAB,591/C')
            self.assertEquals(section.independent_study_instructor_regid, '8BD26A286A7D11D5A4AE0004AC494FFE')


class TimeScheduleConstructionTest(TestCase):
    def test_by_campus(self):
        time_schedule_constructions = [
            TimeScheduleConstruction(campus='Seattle', is_on=False),
            TimeScheduleConstruction(campus='Tacoma', is_on=False),
            TimeScheduleConstruction(campus='Bothell', is_on=True),
        ]
        term = Term(year=2013, quarter='summer')
        term.time_schedule_construction = time_schedule_constructions
        section = Section(term=term)

        for campus in ['Seattle', 'Tacoma', 'Bothell', 'PCE', '']:
            section.course_campus = campus
            self.assertEquals(is_time_schedule_construction(section),
                    True if campus == 'Bothell' else False,
                        'Campus: %s' % section.course_campus)
