from django.conf import settings
from django.utils.timezone import utc
from sis_provisioner.dao.user import (
    valid_net_id, valid_gmail_id, is_group_member)
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.course import (
    group_section_sis_id, valid_academic_course_sis_id)
from sis_provisioner.dao.canvas import get_sis_enrollments_for_user_in_course
from sis_provisioner.exceptions import (
    UserPolicyException, GroupPolicyException, GroupNotFoundException,
    GroupUnauthorizedException, CoursePolicyException)
from sis_provisioner.models import (
    Group as GroupModel, CourseMember as CourseMemberModel, User as UserModel,
    GroupMemberGroup as GroupMemberGroupModel, Enrollment as EnrollmentModel,
    PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH, PRIORITY_IMMEDIATE)
from restclients_core.exceptions import DataFailureException
from uw_gws.models import GroupMember
import xml.etree.ElementTree as ET
from logging import getLogger
import datetime
import re

log_prefix = 'GROUP:'
re_parser = re.compile(b'^(<.*>)[^>]*$')


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

    def _parse(self, message):
        return ET.fromstring(re_parser.sub(r'\g<1>', message))


class UWGroupDispatch(Dispatch):
    """
    Canvas Enrollment Group Event Dispatcher
    """
    def __init__(self, config, message=None):
        super(UWGroupDispatch, self).__init__(config, message)
        self._valid_members = []

    def _find_group_models(self, group_id):
        return GroupModel.objects.filter(group_id=group_id,
                                         priority__gt=PRIORITY_NONE,
                                         is_deleted__isnull=True)

    def mine(self, group):
        self._groups = self._find_group_models(group)
        self._membergroups = GroupMemberGroupModel.objects.filter(
            group_id=group)
        return len(self._groups) > 0 or len(self._membergroups) > 0

    def update_members(self, group_id, message):
        # body contains list of members to be added or removed
        group_id = message.findall('./name')[0].text
        reg_id = message.findall('./regid')[0].text
        member_count = 0

        for el in message.findall('./add-members/add-member'):
            member = GroupMember(name=el.text, type=el.attrib['type'])
            self._process_group_member(group_id, member, is_deleted=None)
            member_count += 1

        for el in message.findall('./delete-members/delete-member'):
            member = GroupMember(name=el.text, type=el.attrib['type'])
            self._process_group_member(group_id, member, is_deleted=True)
            member_count += 1

        self._log.info('{} UPDATE membership for {}'.format(
            log_prefix, group_id))

        return member_count

    def delete_group(self, group_id, message):
        group_id = message.findall('./name')[0].text
        reg_id = message.findall('./regid')[0].text

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        # mark group as delete and ready for import
        GroupModel.objects.filter(
            group_id=group_id, is_deleted__isnull=True).update(
                is_deleted=True, deleted_date=now, deleted_by='gws-event',
                priority=PRIORITY_IMMEDIATE)

        # mark member groups
        membergroups = GroupMemberGroupModel.objects.filter(
            group_id=group_id, is_deleted__isnull=True)
        membergroups.update(is_deleted=True)

        # mark associated root groups for import
        for membergroup in membergroups:
            GroupModel.objects.filter(
                group_id=membergroup.root_group_id,
                is_deleted__isnull=True).update(priority=PRIORITY_IMMEDIATE)

        self._log.info('{} DELETE {}'.format(log_prefix, group_id))

        return 1

    def change_subject_name(self, group_id, message):
        # body contains old and new subject names (id)
        # normalize 'change-subject-name' event
        old_name = message.findall('./subject/old-name')[0].text
        new_name = message.findall('./subject/new-name')[0].text

        GroupModel.objects.filter(
            group_id=old_name).update(group_id=new_name)
        GroupMemberGroupModel.objects.filter(
            group_id=old_name).update(group_id=new_name)
        GroupMemberGroupModel.objects.filter(
            root_group_id=old_name).update(root_group_id=new_name)

        self._log.info('{} UPDATE change-subject-name {} to {}'.format(
            log_prefix, old_name, new_name))

        return 1

    def _process_group_member(self, group_id, member, is_deleted):
        for group in self._groups:
            self._update_group(group, member, is_deleted)

        for member_group in self._membergroups:
            if not member_group.is_deleted:
                for group in self._find_group_models(
                        member_group.root_group_id):
                    self._update_group(group, member, is_deleted)

    def _update_group(self, group, member, is_deleted):
        if member.is_group():
            self._update_group_member_group(group, member.name, is_deleted)
        elif member.is_uwnetid() or member.is_eppn():
            try:
                if member.name not in self._valid_members:
                    if member.is_uwnetid():
                        valid_net_id(member.name)
                    elif member.is_eppn():
                        valid_gmail_id(member.name)
                    self._valid_members.append(member.name)

                self._update_group_member(group, member, is_deleted)
            except UserPolicyException:
                self._log.info('{} IGNORE invalid user {}'.format(
                    log_prefix, member.name))
        else:
            self._log.info('{} IGNORE member type {} ({})'.format(
                log_prefix, member.type, member.name))

    def _update_group_member_group(self, group, member_group, is_deleted):
        try:
            # validity is confirmed by act_as
            (valid, invalid, member_groups) = get_effective_members(
                member_group, act_as=group.added_by)
        except GroupNotFoundException as err:
            GroupMemberGroupModel.objects.filter(
                group_id=member_group).update(is_deleted=True)
            self._log.info('{} REMOVED member group {} not in {}'.format(
                log_prefix, member_group, group.group_id))
            return
        except (GroupPolicyException, GroupUnauthorizedException) as err:
            self._log.info('{} IGNORE {}: {}'.format(
                log_prefix, group.group_id, err))
            return

        for member in valid:
            self._update_group_member(group, member, is_deleted)

        for mg in [member_group] + member_groups:
            (gmg, created) = GroupMemberGroupModel.objects.get_or_create(
                group_id=mg, root_group_id=group.group_id)
            gmg.is_deleted = is_deleted
            gmg.save()

    def _update_group_member(self, group, member, is_deleted):
        # validity is assumed if the course model exists
        if member.is_uwnetid():
            user_id = member.name
        elif member.is_eppn():
            user_id = valid_gmail_id(member.name)
        else:
            return

        try:
            (cm, created) = CourseMemberModel.objects.get_or_create(
                name=user_id, type=member.type,
                course_id=group.course_id, role=group.role)
        except CourseMemberModel.MultipleObjectsReturned:
            models = CourseMemberModel.objects.filter(
                name=user_id, type=member.type,
                course_id=group.course_id, role=group.role)
            self._log.debug('{} MULTIPLE ({}): {} in {} as {}'.format(
                log_prefix, len(models), user_id, group.course_id,
                group.role))
            cm = models[0]
            created = False
            for m in models[1:]:
                m.delete()

        if is_deleted:
            # user in other member groups not deleted
            if self._user_in_member_group(group, member):
                is_deleted = None
        elif self._user_in_course(group, member):
            # official student/instructor not added via group
            is_deleted = True

        cm.is_deleted = is_deleted
        cm.priority = PRIORITY_DEFAULT if not cm.queue_id else PRIORITY_HIGH
        cm.save()

        self._log.info('{} {} {} to {} as {}'.format(
            log_prefix, 'DELETED' if is_deleted else 'ACTIVE',
            user_id, group.course_id, group.role))

    _MEMBER_CACHE = {}

    def _user_in_member_group(self, group, member):
        if self._has_member_groups(group):
            key = '{}:{}:{}'.format(
                group.group_id, member.name, group.added_by)

            if key not in UWGroupDispatch._MEMBER_CACHE:
                UWGroupDispatch._MEMBER_CACHE[key] = is_group_member(
                    group.group_id, member.name, act_as=group.added_by)

            return UWGroupDispatch._MEMBER_CACHE[key]

        return False

    def _user_in_course(self, group, member):
        # academic course?
        try:
            valid_academic_course_sis_id(group.course_id)
        except CoursePolicyException:
            return False

        # provisioned to academic section?
        try:
            user = UserModel.objects.get(net_id=member.name)
            EnrollmentModel.objects.get(
                reg_id=user.reg_id,
                course_id__startswith=group.course_id,
                status='active')
            return True
        except UserModel.DoesNotExist:
            return False
        except EnrollmentModel.DoesNotExist:
            pass

        # inspect Canvas Enrollments
        try:
            canvas_enrollments = get_sis_enrollments_for_user_in_course(
                user.reg_id, group.course_id)
            if len(canvas_enrollments):
                return True
        except DataFailureException as err:
            if err.status == 404:
                pass  # No enrollment
            else:
                raise

        return False

    def _has_member_groups(self, group):
        return GroupMemberGroupModel.objects.filter(
            root_group_id=group.group_id,
            is_deleted__isnull=True).count() > 0


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
