from django.test import TestCase
from django.conf import settings
from sis_provisioner.dao.course import get_section_by_label
from sis_provisioner.models import Curriculum
from sis_provisioner.exceptions import CoursePolicyException


class CurriculumModelTest(TestCase):
    def test_canvas_account_id(self):
        with self.settings(
                LMS_OWNERSHIP_SUBACCOUNT={
                    'PCE_OL': 'uwcourse:uweo:ol-managed',
                    'PCE_NONE': 'uwcourse:uweo:noncredit-campus-managed'},
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            section = get_section_by_label('2013,spring,TRAIN,101/A')

            section.lms_ownership = 'Seattle'
            section.lms_ownership = None
            self.assertRaises(CoursePolicyException,
                              Curriculum.objects.canvas_account_id, section)

            section.course_campus = 'PCE'
            self.assertEquals(Curriculum.objects.canvas_account_id(section),
                              'uwcourse:uweo:noncredit-campus-managed')

            section.lms_ownership = 'PCE_OL'
            self.assertEquals(Curriculum.objects.canvas_account_id(section),
                              'uwcourse:uweo:ol-managed')
