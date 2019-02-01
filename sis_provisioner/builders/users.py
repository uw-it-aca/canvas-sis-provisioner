from sis_provisioner.builders import Builder
from sis_provisioner.dao.user import get_person_by_netid
from sis_provisioner.exceptions import UserPolicyException
from restclients_core.exceptions import DataFailureException


class UserBuilder(Builder):
    """
    Generates the import data for the passed list of User models.
    """
    def _process(self, user):
        try:
            person = get_person_by_netid(user.net_id)
            self.add_user_data_for_person(person, force=True)
        except (UserPolicyException, DataFailureException) as err:
            self.logger.info('Skip user {}: {}'.format(user.reg_id, err))
