# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase
from sis_provisioner.builders.groups import GroupBuilder, SetMember


class GroupBuilderTest(TestCase):
    def test_group_builder(self):
        builder = GroupBuilder()
        self.assertEqual(builder.build(), None)


class SetMemberTest(TestCase):
    def test_set_member(self):
        member1 = SetMember('Javerage', 'StudentEnrollment')
        self.assertEqual(member1.login, 'javerage')
        self.assertEqual(member1.role, 'Student')

        member2 = SetMember('javerage', 'student')
        self.assertEqual(member2.login, 'javerage')
        self.assertEqual(member2.role, 'student')

        member3 = SetMember('javerage', 'TAEnrollment')

        self.assertTrue(member1 == member2)
        self.assertFalse(member1 == member3)

        self.assertTrue(hash(member1) == hash(member2))
        self.assertFalse(hash(member1) == hash(member3))
