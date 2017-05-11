from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import SectionCSV
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.user import valid_gmail_id
from sis_provisioner.dao.course import (
    valid_adhoc_course_sis_id, valid_academic_course_sis_id,
    group_section_sis_id, group_section_name)
from sis_provisioner.dao.canvas import (
    get_course_by_id, get_course_by_sis_id, update_course_sis_id,
    get_sis_enrollments_for_course, ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.models import Group, GroupMemberGroup, CourseMember
from sis_provisioner.exceptions import (
    CoursePolicyException, GroupPolicyException)
from restclients_core.exceptions import DataFailureException


class GroupBuilder(Builder):
    def _init_build(self, **kwargs):
        self.delta = kwargs.get('delta', True)
        self.cached_course_enrollments = {}
        self.items = list(set(self.items))

    def _process(self, course_id):
        try:
            self._verify_canvas_course(course_id)
        except DataFailureException as err:
            if err.status == 404:
                Group.objects.deprioritize_course(course_id)
                self.logger.info("Drop group sync for deleted course %s" % (
                    course_id))
            else:
                self._requeue_course(course_id, err)
            return

        group_section_id = group_section_sis_id(course_id)
        self.data.add(SectionCSV(
            section_id=group_section_id, course_id=course_id,
            name=group_section_name()))

        # Get the enrollments for academic courses from Canvas, excluding
        # ad-hoc and group sections
        try:
            valid_academic_course_sis_id(course_id)
            if course_id not in self.cached_course_enrollments:
                canvas_enrollments = get_sis_enrollments_for_course(course_id)
                self.cached_course_enrollments[course_id] = canvas_enrollments

        except CoursePolicyException:
            self.cached_course_enrollments[course_id] = []
        except DataFailureException as err:
            self._requeue_course(course_id, err)
            return

        current_members = []
        for group in Group.objects.get_active_by_course(course_id):
            try:
                current_members.extend(self._get_current_members(group))

            except DataFailureException as err:
                self._requeue_course(course_id, err)
                return

            # skip on any group policy exception
            except GroupPolicyException as err:
                self.logger.info("Skip group %s (%s)" % (group.group_id, err))

        cached_members = CourseMember.objects.get_by_course(course_id)
        for member in cached_members:
            match = next((m for m in current_members if m == member), None)

            if match is None:
                if not self.delta or not member.is_deleted:
                    try:
                        self.add_group_enrollment_data(
                            member, group_section_id, member.role,
                            status=ENROLLMENT_DELETED)
                    except Exception as err:
                        self.logger.info("Skip group member %s (%s)" % (
                            member.name, err))

                member.deactivate()

        for member in current_members:
            match = next((m for m in cached_members if m == member), None)

            # new or previously removed member
            if not self.delta or match is None or match.is_deleted:
                try:
                    self.add_group_enrollment_data(
                        member, group_section_id, member.role,
                        status=ENROLLMENT_ACTIVE)
                except Exception as err:
                    self.logger.info("Skip group member %s (%s)" % (
                        member.name, err))

                if match is None:
                    member.save()
                elif match.is_deleted:
                    match.activate()

    def _verify_canvas_course(self, course_id):
        try:
            valid_adhoc_course_sis_id(course_id)
            (prefix, canvas_course_id) = course_id.split('_')
            canvas_course = get_course_by_id(canvas_course_id)
        except CoursePolicyException:
            canvas_course = get_course_by_sis_id(course_id)

        if canvas_course.sis_course_id is None:
            update_course_sis_id(canvas_course.course_id, course_id)

    def _get_current_members(self, group):
        (members, invalid_members, member_groups) = get_effective_members(
            group.group_id, act_as=group.added_by)

        self._reconcile_member_groups(group, member_groups)

        for member in invalid_members:
            self.logger.info("Skip group member %s (%s)" % (
                member.name, member.error))

        current_members = []
        for member in members:
            login_id = member.name
            if member.is_uwnetid():
                user_id = member.name
            elif member.is_eppn():
                user_id = valid_gmail_id(member.name)
            else:
                continue

            # Skip members already in academic course sections, removing
            # from -group section
            enrollments = self.cached_course_enrollments[group.course_id]
            match = next((m for m in enrollments if (
                m.login_id is not None and
                m.login_id.lower() == login_id.lower())), None)

            if match:
                self.logger.info("Skip group member %s (present in %s)" % (
                    member.name, match.sis_section_id))
                continue

            course_member = CourseMember(course_id=group.course_id,
                                         name=user_id,
                                         member_type=member.member_type,
                                         role=group.role)
            course_member.login = login_id
            current_members.append(course_member)
        return current_members

    def _reconcile_member_groups(self, group, member_group_ids):
        for member_group_id in member_group_ids:
            (gmg, created) = GroupMemberGroup.objects.get_or_create(
                group_id=member_group_id, root_group_id=group.group_id)

            if not created:
                gmg.activate()

        for gmg in GroupMemberGroup.objects.get_active_by_root(group.group_id):
            if gmg.group_id not in member_group_ids:
                gmg.deactivate()

    def _requeue_course(self, course_id, err):
        Group.objects.dequeue_course(course_id)
        self.logger.info("Requeue group sync for course %s: %s" % (
            course_id, err))
