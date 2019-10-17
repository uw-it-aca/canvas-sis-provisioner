from django.conf import settings
from sis_provisioner.dao.user import valid_net_id, valid_gmail_id
from sis_provisioner.exceptions import UserPolicyException
from sis_provisioner.models import (
    Group, GroupMemberGroup, PRIORITY_HIGH, PRIORITY_IMMEDIATE)
import xml.etree.ElementTree as ET
from logging import getLogger
import re

log_prefix = 'GROUP:'
re_parser = re.compile(r'^.*(<group.*/group>).*$', re.MULTILINE | re.DOTALL)


class Dispatch(object):
    """
    Base class for dispatching on actions within a UW GWS Event
    """
    def __init__(self, config, message=None):
        self._log = getLogger(__name__)
        self._settings = config
        self._message = message

    def mine(self, group):
        return False

    def run(self, action, group, message):
        try:
            return {
                'update-members': self.update_members,
                'put-group': self.put_group,
                'delete-group': self.delete_group,
                'put-members': self.put_members,
                'change-subject-name': self.change_subject_name,
                'no-action': self.no_action
            }[action](group, self._parse(message))
        except KeyError:
            self._log.info('{} UNKNOWN {} for {}'.format(
                log_prefix, action, group))
            return 0

    def update_members(self, group_id, message):
        self._log.info('{} IGNORE update-members for {}'.format(
            log_prefix, group_id))
        return 0

    def put_group(self, group_id, message):
        self._log.info('{} IGNORE put-group {}'.format(log_prefix, group_id))
        return 0

    def delete_group(self, group_id, message):
        self._log.info('{} IGNORE delete-group {}'.format(
            log_prefix, group_id))
        return 0

    def put_members(self, group_id, message):
        self._log.info('{} IGNORE put-members for {}'.format(
            log_prefix, group_id))
        return 0

    def change_subject_name(self, group_id, message):
        self._log.info('{} IGNORE change-subject-name for {}'.format(
            log_prefix, group_id))
        return 0

    def no_action(self, group_id, message):
        return 0

    @staticmethod
    def _parse(message):
        message = re_parser.sub(r'\g<1>', message.decode('utf-8'))
        return ET.fromstring(message)


class UWGroupDispatch(Dispatch):
    """
    Canvas Enrollment Group Event Dispatcher
    """
    def mine(self, group_id):
        return (Group.objects.filter(group_id=group_id).count() or
                GroupMemberGroup.objects.filter(group_id=group_id).count())

    @staticmethod
    def _valid_member(login_id):
        try:
            valid_net_id(login_id)
            return 1
        except UserPolicyException:
            try:
                valid_gmail_id(login_id)
                return 1
            except UserPolicyException:
                pass
        return 0

    def update_members(self, group_id, message):
        # body contains list of members to be added or removed
        group_id = message.findall('./name')[0].text
        member_count = 0

        for el in message.findall('./add-members/add-member'):
            member_count += self._valid_member(el.text)

        for el in message.findall('./delete-members/delete-member'):
            member_count += self._valid_member(el.text)

        if member_count > 0:
            for group in Group.objects.get_active_by_group(group_id):
                group.update_priority(PRIORITY_HIGH)

            for mgroup in GroupMemberGroup.objects.get_active_by_group(
                    group_id):
                for group in Group.objects.get_active_by_group(
                        mgroup.root_group_id):
                    group.update_priority(PRIORITY_HIGH)

            self._log.info('{} UPDATE membership for {}'.format(
                log_prefix, group_id))

        return member_count

    def delete_group(self, group_id, message):
        group_id = message.findall('./name')[0].text

        # mark group as deleted and ready for import
        Group.objects.delete_group_not_found(group_id)

        # mark associated root groups for import
        for mgroup in GroupMemberGroup.objects.get_active_by_group(group_id):
            mgroup.deactivate()

            for group in Group.objects.get_active_by_group(
                    mgroup.root_group_id):
                group.update_priority(PRIORITY_IMMEDIATE)

        self._log.info('{} DELETE {}'.format(log_prefix, group_id))

        return 1

    def change_subject_name(self, group_id, message):
        # body contains old and new subject names (id)
        # normalize 'change-subject-name' event
        old_name = message.findall('./subject/old-name')[0].text
        new_name = message.findall('./subject/new-name')[0].text

        Group.objects.update_group_id(old_name, new_name)
        GroupMemberGroup.objects.update_group_id(old_name, new_name)
        GroupMemberGroup.objects.update_root_group_id(old_name, new_name)

        self._log.info('{} UPDATE change-subject-name {} to {}'.format(
            log_prefix, old_name, new_name))

        return 1


class ImportGroupDispatch(Dispatch):
    """
    Import Group Dispatcher
    """
    def mine(self, group):
        return True if group in settings.SIS_IMPORT_GROUPS else False

    def update_members(self, group, message):
        self._log.info('{} IGNORE canvas user update: {}'.format(
            log_prefix, group))
        return 0


class CourseGroupDispatch(Dispatch):
    """
    Course Group Dispatcher
    """
    def mine(self, group):
        course = ('course_' in group and re.match(
            (r'^course_(20[0-9]{2})'
             r'([a-z]{3})-([a-z\-]+)'
             r'([0-9]{3})([a-z][a-z0-9]?)$'), group))
        if course:
            self._course_sis_id = '-'.join([
                course.group(1),
                {'win': 'winter', 'spr': 'spring', 'sum': 'summer',
                    'aut': 'autumn'}[course.group(2)],
                re.sub(r'\-', ' ', course.group(3).upper()),
                course.group(4), course.group(5).upper()
            ])
            return True
        return False

    def update_members(self, group, message):
        # body contains list of members to be added or removed
        self._log.info('{} IGNORE course group update: {}'.format(
            log_prefix, self._course_sis_id))
        return 0

    def put_group(self, group_id, message):
        self._log.info('{} IGNORE course group put-group: {}'.format(
            log_prefix, group_id))
        return 0
