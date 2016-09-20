from django.test import TestCase
from django.conf import settings
from sis_provisioner.policy import GroupPolicy, GroupPolicyException,\
    GroupNotFoundException


class GroupPolicyTest(TestCase):
    def test_valid_group(self):
        with self.settings(
                UW_GROUP_BLACKLIST=['uw_student', 'uw_staff']):
            policy = GroupPolicy()

            # Valid
            self.assertEquals(policy.valid('u_javerage_test'), None)
            self.assertEquals(policy.valid('uw_faculty'), None)

            # Invalid
            self.assertRaises(GroupPolicyException, policy.valid, '')
            self.assertRaises(GroupPolicyException, policy.valid, '1')
            self.assertRaises(GroupPolicyException, policy.valid, 'uw_student')
            self.assertRaises(GroupPolicyException, policy.valid, 'uw_staff')


class EffectiveMemberTest(TestCase):
    def test_effective_members(self):
        with self.settings(
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):
            policy = GroupPolicy()

            (valid_members, invalid_members, member_groups) = policy.get_effective_members('u_acadev_unittest')

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            (valid_members, invalid_members, member_groups) = policy.get_effective_members('u_acadev_unittest', 'javerage')  # Using act_as

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            self.assertRaises(GroupNotFoundException, policy.get_effective_members, 'u_acadev_fake')
