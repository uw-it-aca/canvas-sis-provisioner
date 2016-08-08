from django.test import TestCase
from django.conf import settings
from restclients.sws.term import get_next_term
from restclients.models.sws import Section
from sis_provisioner.policy import UserPolicy, UserPolicyException,\
    CoursePolicy, CoursePolicyException


class TimeScheduleConstructionTest(TestCase):
    def test_by_campus(self):
        with self.settings(
                RESTCLIENTS_SWS_DAO_CLASS='restclients.dao_implementation.sws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

	    policy = CoursePolicy()

	    term = get_next_term()
            section = Section(term=term)

            for campus in ['Seattle', 'Tacoma', 'Bothell', 'PCE', '']:
                section.course_campus = campus
                self.assertEquals(policy.is_time_schedule_construction(section),
                        True if campus == 'Bothell' else False,
                        'Campus: %s' % section.course_campus)


class GmailPolicyTest(TestCase):
    valid_domains = ['gmail.com', 'google.com', 'googlemail.com']

    def test_valid_domains(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith"

            invalid_domains = [
                "abc.com"
                "",
            ]

            policy = UserPolicy()

            for domain in self.valid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertEquals(policy.valid_gmail_id(user), user, "Valid user: %s" % user)

            for domain in invalid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)

    def test_valid_user(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith@gmail.com"

            valid_users = [
                "JohnSmith@gmail.com",
                "johnsmith@GMail.com",
                "john.smith@gmail.com",
                "john.smith+canvas@gmail.com",
                "john.smith+abc+canvas+@gmail.com",
                ".john.smith@gmail.com",
            ]

            invalid_users = [
                "john@smith@gmail.com",
                "+johnsmith@gmail.com",
                "+@gmail.com",
                ".@gmail.com",
                "@gmail.com",
            ]

            policy = UserPolicy()

            self.assertEquals(policy.valid_gmail_id(default_user), default_user, "Default user is not changed")

            for user in valid_users:
                self.assertEquals(policy.valid_gmail_id(user), default_user, "Valid user: %s" % user)

            for user in invalid_users:
                self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)

        with self.settings(LOGIN_DOMAIN_WHITELIST = []):
            policy = UserPolicy()
            self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)
