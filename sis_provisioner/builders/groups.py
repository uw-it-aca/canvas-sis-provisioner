from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import SectionCSV
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.user import valid_gmail_id
from sis_provisioner.dao.course import (
    valid_adhoc_course_sis_id, group_section_sis_id, group_section_name)
from sis_provisioner.dao.canvas import (
    get_course_by_id, get_course_by_sis_id, update_course_sis_id,
    get_sis_enrollments_for_course, get_group_enrollments_for_course,
    ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.models import Group, GroupMemberGroup
from sis_provisioner.exceptions import (
    CoursePolicyException, GroupPolicyException, EnrollmentPolicyException)
from restclients_core.exceptions import DataFailureException


class GroupBuilder(Builder):
    def _process(self, course_id):
        group_section_id = group_section_sis_id(course_id)

        # Verify that the Canvas course still exists and has a correct sis_id
        try:
            self._verify_canvas_course(course_id)
        except DataFailureException as err:
            if err.status == 404:
                Group.objects.deprioritize_course(course_id)
                self.logger.info(
                    "Drop group sync for deleted course {}".format(course_id))
            else:
                self._requeue_course(course_id, err)
            return

        # Create a lookup for all sis enrollments in the course
        try:
            sis_enrollment_lookup = self.all_sis_section_enrollments(course_id)
        except DataFailureException as err:
            self._requeue_course(course_id, err)
            return

        # Get the Canvas enrollments for the Group section in this course
        try:
            current_enrollments = self.all_group_section_enrollments(course_id)
        except DataFailureException as err:
            if err.status == 404:  # Group section not found
                current_enrollments = set()

                self.data.add(SectionCSV(
                    section_id=group_section_id, course_id=course_id,
                    name=group_section_name()))
            else:
                self._requeue_course(course_id, err)
                return

        # Build a flattened set of current group memberships from GWS
        try:
            current_members = self.all_group_memberships(course_id)
        except DataFailureException as err:
            self._requeue_course(course_id, err)
            return

        # Remove enrollments not in the current group membership from
        # the groups section
        for key in (current_enrollments - current_members):
            try:
                (login, role) = self.parse_key(key)
                self.add_group_enrollment_data(
                    login, group_section_id, role, status=ENROLLMENT_DELETED)
            except DataFailureException as err:
                self.logger.info("Skip group member {}: {}".format(
                    login, err))

        # Add group members not already enrolled to the groups section,
        # unless the user already has an sis enrollment in the course
        for key in (current_members - current_enrollments):
            try:
                (login, role) = self.parse_key(key)

                if login in sis_enrollment_lookup:
                    self.logger.info(
                        "Skip group member {} (present in {})".format(
                            login, sis_enrollments[login]))
                    continue

                self.add_group_enrollment_data(
                    login, group_section_id, role, status=ENROLLMENT_ACTIVE)
            except DataFailureException as err:
                self.logger.info("Skip group member {}: {}".format(
                    login, err))

    def _verify_canvas_course(self, course_id):
        try:
            valid_adhoc_course_sis_id(course_id)
            (prefix, canvas_course_id) = course_id.split('_')
            canvas_course = get_course_by_id(canvas_course_id)
        except CoursePolicyException:
            canvas_course = get_course_by_sis_id(course_id)

        if canvas_course.sis_course_id is None:
            update_course_sis_id(canvas_course.course_id, course_id)

    def all_sis_section_enrollments(self, course_id):
        return dict((e.login_id.lower(), e.sis_section_id) for e in (
            get_sis_enrollments_for_course(course_id)))

    def all_group_section_enrollments(self, course_id):
        group_enrollments = set()
        for enrollment in get_group_enrollments_for_course(course_id):
            key = self.create_key(enrollment.login_id, enrollment.role)
            group_enrollments.add(key)
        return group_enrollments

    def all_group_memberships(self, course_id):
        """
        Returns a flattened dict of current GWS group memberships
        for the course
        """
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
                    key = self.create_key(member.name, group.role)
                    current_members.add(key)

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

    @staticmethod
    def create_key(login_id, role):
        return "{}/{}".format(login_id, role.replace('Enrollment', '')).lower()

    @staticmethod
    def parse_key(key):
        return key.split("/")

    def _requeue_course(self, course_id, err):
        Group.objects.dequeue_course(course_id)
        self.logger.info("Requeue group sync for course {}: {}".format(
            course_id, err))
