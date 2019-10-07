from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import SectionCSV
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.user import valid_gmail_id
from sis_provisioner.dao.course import (
    valid_adhoc_course_sis_id, valid_academic_course_sis_id,
    group_section_sis_id, group_section_name)
from sis_provisioner.dao.canvas import (
    get_course_by_id, get_course_by_sis_id, update_course_sis_id,
    get_sis_enrollments_for_course, get_group_enrollments_for_course,
    ENROLLMENT_ACTIVE, ENROLLMENT_DELETED)
from sis_provisioner.models import Group, GroupMemberGroup
from sis_provisioner.exceptions import (
    CoursePolicyException, GroupPolicyException, EnrollmentPolicyException)
from restclients_core.exceptions import DataFailureException


class GroupBuilder(Builder):
    def _init_build(self, **kwargs):
        self.cached_sis_enrollments = {}
        self.cached_group_enrollments = {}

    def _process(self, course_id):
        try:
            self._verify_canvas_course(course_id)

            # Get the Canvas enrollments for the Group section in this course
            current_enrollments = self.all_group_section_enrollments(course_id)

            # Build a flattened set of current group memberships from GWS
            current_members = self.all_group_memberships(course_id)

        except DataFailureException as err:
            if err.status == 404:
                Group.objects.deprioritize_course(course_id)
                self.logger.info(
                    "Drop group sync for deleted course {}".format(course_id))
            else:
                self._requeue_course(course_id, err)
            return

        group_section_id = group_section_sis_id(course_id)
        self.data.add(SectionCSV(
            section_id=group_section_id, course_id=course_id,
            name=group_section_name()))

        # Find enrollments not in group membership
        for key in (current_enrollments - current_members):
            try:
                (login, role) = parse_key(key)
                self.add_group_enrollment_data(
                    login, group_section_id, role, status=ENROLLMENT_DELETED)
            except DataFailureException as err:
                self.logger.info("Skip group member {} ({})".format(
                    login, err))

        # Find group members that aren't enrolled
        for key in (current_members - current_enrollments):
            try:
                (login, role) = parse_key(key)
                self.add_group_enrollment_data(
                    login, group_section_id, role, status=ENROLLMENT_ACTIVE)
            except DataFailureException as err:
                self.logger.info("Skip group member {} ({})".format(
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

    def _check_sis_enrollments_for_member(self, login_id, course_id):
        """
        Check the group member against the Canvas SIS enrollments for the
        course.  Matchng users will be rejected.
        """
        if course_id not in self.cached_sis_enrollments:
            try:
                valid_academic_course_sis_id(course_id)

                self.cached_sis_enrollments[course_id] = dict(
                    (e.login_id.lower(), e.sis_section_id) for e in (
                        get_sis_enrollments_for_course(course_id)))

            except CoursePolicyException:
                self.cached_sis_enrollments[course_id] = {}

        if login_id in self.cached_sis_enrollments[course_id]:
            sis_section_id = self.cached_sis_enrollments[course_id][login_id]
            self.logger.info("Skip group member {} (present in {})".format(
                    login_id, sis_section_id))
            raise EnrollmentPolicyException

    def all_group_section_enrollments(self, course_id):
        if course_id not in self.cached_group_enrollments:
            self.cached_group_enrollments[course_id] = set()
            for enrollment in get_group_enrollments_for_course(course_id):
                self.cached_group_enrollments[course_id].add(
                    create_key(enrollment.login_id, enrollment.role))

        return self.cached_group_enrollments[course_id]

    def all_group_memberships(self, course_id):
        """
        Returns a flattened dict of current GWS group memberships
        for the course
        """
        current_members = set()
        for group in Group.objects.get_active_by_course(course_id):
            try:
                current_members.update(self._get_group_members(group))

            # Skip on any group policy exception
            except GroupPolicyException as err:
                self.logger.info(
                    "Skip group {} ({})".format(group.group_id, err))
        return current_members

    def _get_group_members(self, group):
        (members, invalid_members, member_groups) = get_effective_members(
            group.group_id, act_as=group.added_by)

        self._reconcile_member_groups(group, member_groups)

        for member in invalid_members:
            self.logger.info("Skip group member {} ({})".format(
                member.name, member.error))

        valid_members = set()
        for member in members:
            try:
                self._check_sis_enrollments_for_member(member.name, course_id)
            except EnrollmentPolicyException:
                continue

            valid_members.add(create_key(member.name, group.role))

        return valid_members

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
        return "{}/{}".format(login_id.lower(), role.lower())

    @staticmethod
    def parse_key(key):
        return key.split("/")

    def _requeue_course(self, course_id, err):
        Group.objects.dequeue_course(course_id)
        self.logger.info("Requeue group sync for course {}: {}".format(
            course_id, err))
