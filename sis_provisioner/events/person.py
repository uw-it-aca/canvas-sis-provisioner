from sis_provisioner.events import SISProvisionerProcessor
from sis_provisioner.models import User, PRIORITY_HIGH
from sis_provisioner.models.events import PersonLog
from uw_sws.models import Person as PersonModel

log_prefix = 'PERSON:'
QUEUE_SETTINGS_NAME = 'PERSON_V1'


class PersonProcessor(SISProvisionerProcessor):
    """
    Collects Person Change Event described by
    """
    _logModel = PersonLog

    # What we expect in a v2 person message
    _eventMessageType = 'uw-person-change-v1'
    _eventMessageVersion = '1'

    def __init__(self, queue_settings_name=QUEUE_SETTINGS_NAME):
        super(PersonProcessor, self).__init__(queue_settings_name)

    def process_inner_message(self, json_data):
        current = json_data['Current']
        previous = json_data['Previous']
        net_id = current['UWNetID'] if current else previous['UWNetID']
        if not net_id:
            self.logger.info('{} IGNORE missing uwnetid for {}'.format(
                log_prefix,
                current['RegID'] if current else previous['RegID']))
            return

        # Preferred name, net_id or reg_id change?
        if (not (previous and current) or
                current['StudentName'] != previous['StudentName'] or
                current['FirstName'] != previous['FirstName'] or
                current['LastName'] != previous['LastName'] or
                current['UWNetID'] != previous['UWNetID'] or
                current['RegID'] != previous['RegID']):

            user = User.objects.update_priority(
                PersonModel(uwregid=current['RegID'], uwnetid=net_id),
                PRIORITY_HIGH)

            if user is not None:
                self.record_success_to_log(event_count=1)
