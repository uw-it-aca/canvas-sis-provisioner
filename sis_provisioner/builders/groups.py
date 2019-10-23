from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import SectionCSV
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.course import (
    valid_adhoc_course_sis_id, valid_academic_section_sis_id,
    group_section_sis_id, group_section_name)
from sis_provisioner.dao.canvas import (
    get_course_by_id, get_course_by_sis_id, get_section_by_sis_id,
    update_course_sis_id, get_enrollments_for_course_by_sis_id,
    ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.models import Group, GroupMemberGroup
from sis_provisioner.exceptions import (
    CoursePolicyException, GroupPolicyException)
from restclients_core.exceptions import DataFailureException


class SetMember(object):
    def __init__(self, login, role):
        self.login = login.lower()
        self.role = role.replace('Enrollment', '')

    def __eq__(self, other):
        return (self.login == other.login and self.role == other.role)

    def __hash__(self):
        return hash((self.login, self.role))


class GroupBuilder(Builder):
    def _process(self, course_id):
        group_section_id = group_section_sis_id(course_id)

        try:
            self.verify_canvas_course(course_id)
        except DataFailureException as err:
            if err.status == 404:
                Group.objects.deprioritize_course(course_id)
                self.logger.info(
                    "Drop group sync for deleted course {}".format(course_id))
            else:
                self._requeue_course(course_id, err)
            return

        try:
            # Get the enrollments for SIS and Group sections in this course
            (sis_enrollments, group_enrollments) = self.all_course_enrollments(
                course_id)

            # Build a flattened set of current group memberships from GWS
            current_members = self.all_group_memberships(course_id)

        except DataFailureException as err:
            self._requeue_course(course_id, err)
            return

        # Remove enrollments not in the current group membership from
        # the groups section
        for member in (group_enrollments - current_members):
            try:
                self.add_group_enrollment_data(
                    member.login, group_section_id, member.role,
                    status=ENROLLMENT_DELETED)
            except DataFailureException as err:
                self.logger.info("Skip remove group member {}: {}".format(
                    member.login, err))

        # Add group members not already enrolled to the groups section,
        # unless the user already has an sis enrollment in the course
        for member in (current_members - group_enrollments):
            if member.login in sis_enrollments:
                self.logger.info(
                    "Skip add group member {} (present in {})".format(
                        member.login, sis_enrollments[member.login]))
                continue

            try:
                self.add_group_enrollment_data(
                    member.login, group_section_id, member.role,
                    status=ENROLLMENT_ACTIVE)
            except DataFailureException as err:
                self.logger.info("Skip add group member {}: {}".format(
                    member.login, err))

        # Remove any existing group enrollments that also have an
        # sis enrollment in the course
        for member in group_enrollments:
            if member.login in sis_enrollments:
                self.add_group_enrollment_data(
                    member.login, group_section_id, member.role,
                    status=ENROLLMENT_DELETED)
                self.logger.info(
                    "Remove group enrollment {} (present in {})".format(
                        member.login, sis_enrollments[member.login]))

    def verify_canvas_course(self, course_id):
        """
        Verify that the Canvas course still exists, has a correct sis_id, and
        contains a UW Group section.
        """
        try:
            valid_adhoc_course_sis_id(course_id)
            (prefix, canvas_course_id) = course_id.split('_')
            canvas_course = get_course_by_id(canvas_course_id)
        except CoursePolicyException:
            canvas_course = get_course_by_sis_id(course_id)

        if canvas_course.sis_course_id is None:
            update_course_sis_id(canvas_course.course_id, course_id)

        group_section_id = group_section_sis_id(course_id)
        try:
            section = get_section_by_sis_id(group_section_id)
        except DataFailureException as err:
            if err.status == 404:
                self.data.add(SectionCSV(
                    section_id=group_section_id, course_id=course_id,
                    name=group_section_name()))
            else:
                raise

    def all_course_enrollments(self, course_id):
        group_section_id = group_section_sis_id(course_id)
        sis_enrollments = {}
        group_enrollments = set()
        for enr in get_enrollments_for_course_by_sis_id(course_id):
            # Split the enrollments into sis and group enrollments,
            # discarding enrollments for adhoc sections
            try:
                valid_academic_section_sis_id(enr.sis_section_id)
                sis_enrollments[enr.login_id.lower()] = enr.sis_section_id

            except CoursePolicyException:
                if enr.sis_section_id == group_section_id:
                    group_enrollments.add(SetMember(enr.login_id, enr.role))

        return (sis_enrollments, group_enrollments)

    def all_group_memberships(self, course_id):
        current_members = set()
        for group in Group.objects.get_active_by_course(course_id):
            try:
                (members, invalid_members,
                    member_groups) = get_effective_members(
                        group.group_id, act_as=group.added_by)

                self._reconcile_member_groups(group, member_groups)

                for member in invalid_members:
                    self.logger.info("Skip group member {} ({})".format(
                        member.name, member.error))

                for member in members:
                    current_members.add(SetMember(member.name, group.role))

            # Skip on any group policy exception
            except GroupPolicyException as err:
                self.logger.info(
                    "Skip group {} ({})".format(group.group_id, err))
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
        self.logger.info("Requeue group sync for course {}: {}".format(
            course_id, err))
