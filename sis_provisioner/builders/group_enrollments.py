from sis_provisioner.builders import Builder
from sis_provisioner.dao.course import group_section_sis_id
from sis_provisioner.dao.canvas import ENROLLMENT_ACTIVE, ENROLLMENT_DELETED


class GroupEnrollmentBuilder(Builder):
    def _process(self, member):
        section_id = group_section_sis_id(member.course_id)

        status = ENROLLMENT_DELETED if (
            member.is_deleted) else ENROLLMENT_ACTIVE

        if member.is_eppn():
            member.login = member.name

        try:
            self.add_group_enrollment_data(member, section_id, member.role,
                                           status)

        except Exception as err:
            self.logger.info("Skip group member %s (%s)" % (member.name, err))
