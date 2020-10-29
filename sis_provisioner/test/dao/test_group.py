from django.test import TestCase, override_settings
from django.utils.timezone import utc
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.group import *
from sis_provisioner.exceptions import (
    GroupPolicyException, GroupNotFoundException)
from datetime import datetime, timedelta
from uw_gws.utilities import fdao_gws_override
from uw_pws.util import fdao_pws_override
import mock


@fdao_gws_override
@fdao_pws_override
class GroupPolicyTest(TestCase):
    @override_settings(UW_GROUP_BLACKLIST=['uw_student', 'uw_staff'])
    def test_valid_group(self):
        # Valid
        self.assertEquals(valid_group_id('u_javerage_test'), None)
        self.assertEquals(valid_group_id('uw_faculty'), None)

        # Invalid
        self.assertRaises(GroupPolicyException, valid_group_id, None)
        self.assertRaises(GroupPolicyException, valid_group_id, '')
        self.assertRaises(GroupPolicyException, valid_group_id, '1')
        self.assertRaises(GroupPolicyException, valid_group_id, 'uw_student')
        self.assertRaises(GroupPolicyException, valid_group_id, 'uw_staff')


@fdao_gws_override
@fdao_pws_override
class GetGroupTest(TestCase):
    @mock.patch.object(GWS, 'get_group_by_id')
    def test_get_group(self, mock_method):
        r = get_group('javerage', '123')
        mock_method.assert_called_with('123')

    @mock.patch.object(GWS, 'search_groups')
    def test_search_groups(self, mock_method):
        r = search_groups('javerage')
        mock_method.assert_called_with(scope='all')

        r = search_groups('javerage', name='foo')
        mock_method.assert_called_with(name='foo*', scope='all')

        r = search_groups('javerage', name='foo*')
        mock_method.assert_called_with(name='foo*', scope='all')

    @mock.patch('sis_provisioner.dao.group.GWS')
    def test_gws_constructor(self, mock_object):
        r = get_group('javerage', '123')
        mock_object.assert_called_with(act_as='javerage')

        r = search_groups('javerage')
        mock_object.assert_called_with(act_as='javerage')


@fdao_gws_override
@fdao_pws_override
class GroupModifiedTest(TestCase):
    def test_modified_group(self):
        mtime = datetime.now()
        self.assertRaises(
            GroupNotFoundException, is_modified_group,
            'u_does_not_exist', mtime)

        mtime = datetime(2000, 10, 10, 0, 0, 0).replace(tzinfo=utc)
        self.assertEquals(is_modified_group('u_acadev_tester', mtime), True)

        mtime = datetime(2020, 10, 10, 0, 0, 0).replace(tzinfo=utc)
        self.assertEquals(is_modified_group('u_acadev_tester', mtime), False)

        mtime = None
        self.assertRaises(
            TypeError, is_modified_group, 'u_acadev_tester', mtime)


@fdao_gws_override
@fdao_pws_override
class SISImportMembersTest(TestCase):
    @override_settings(
        SIS_IMPORT_GROUPS=['u_acadev_unittest', 'u_acadev_tester'])
    def test_sis_import_members(self):
        members = get_sis_import_members()

        self.assertEquals(len(members), 5)

    @override_settings(SIS_IMPORT_GROUPS=['u_does_not_exist'])
    def test_sis_import_members_none(self):
        self.assertRaises(DataFailureException, get_sis_import_members)


@fdao_gws_override
@fdao_pws_override
class EffectiveMemberTest(TestCase):
    @override_settings(UW_GROUP_BLACKLIST=['uw_student', 'uw_staff'])
    def test_effective_members(self):
        valid_members, invalid_members, member_groups = get_effective_members(
            'u_acadev_unittest')

        self.assertEquals(len(valid_members), 2)
        self.assertEquals(len(invalid_members), 0)
        self.assertEquals(len(member_groups), 0)

        valid_members, invalid_members, member_groups = get_effective_members(
            'u_acadev_unittest', 'javerage')  # Using act_as

        self.assertEquals(len(valid_members), 2)
        self.assertEquals(len(invalid_members), 0)
        self.assertEquals(len(member_groups), 0)

        self.assertRaises(
            GroupNotFoundException, get_effective_members, 'u_acadev_fake')
