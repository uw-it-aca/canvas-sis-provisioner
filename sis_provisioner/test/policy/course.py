from django.test import TestCase
from django.conf import settings
from restclients.models.sws import Term, Section, TimeScheduleConstruction
from sis_provisioner.policy import CoursePolicy, CoursePolicyException


class TimeScheduleConstructionTest(TestCase):
    def test_by_campus(self):
        policy = CoursePolicy()

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
            self.assertEquals(policy.is_time_schedule_construction(section),
                    True if campus == 'Bothell' else False,
                        'Campus: %s' % section.course_campus)
