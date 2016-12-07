from sis_provisioner.builders import Builder
from sis_provisioner.dao.user import get_person_by_netid
from sis_provisioner.exceptions import UserPolicyException


class UserBuilder(Builder):
    """
    Generates the import data for the passed list of User models.
    """
    def __init__(self, users):
        super(UserBuilder, self).__init__()
        self.users = users

    def build(self):
        for user in self.users:
            try:
                person = get_person_by_netid(user.net_id)
                self.add_user_data_for_person(person, force=True)
            except UserPolicyException as err:
                self.logger.info('Skip user %s: %s' % (user.reg_id, err))

        return self.write()
