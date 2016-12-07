from sis_provisioner.builders import Builder
from sis_provisioner.dao.course import group_section_sis_id
from sis_provisioner.models import Enrollment


class GroupEnrollmentBuilder(Builder):
    def __init__(self, group_members):
        super(GroupEnrollmentBuilder, self).__init__()
        self.group_members = group_members

    def build(self):
        for member in self.group_members:
            section_id = group_section_sis_id(member.course_id)

            status = Enrollment.DELETED_STATUS if (
                member.is_deleted) else Enrollment.ACTIVE_STATUS

            if member.is_eppn():
                member.login = member.name

            try:
                self.add_group_enrollment_data(member, section_id,
                                               member.role, status)

            except Exception as err:
                self.logger.info("Skip group member %s (%s)" % (
                    member.name, err))

        return self.write()
