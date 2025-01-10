# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.events import SISProvisionerProcessor
from sis_provisioner.models.user import User
from sis_provisioner.models.events import PersonLog
from uw_sws.models import Person as PersonModel
import json
import os

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

    def __init__(self):
        super(PersonProcessor, self).__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME, is_encrypted=False)

    def process_message_body(self, json_data):
        if os.getenv('LOG_PERSON_EVENT_DATA'):
            self.logger.info('Event data: {}'.format(json.dumps(json_data)))

        current = json_data['Current']
        previous = json_data['Previous']

        net_id = current['UWNetID'] if current else previous['UWNetID']
        if net_id:
            # Preferred name, net_id or reg_id change?
            if (not (previous and current) or
                    current['StudentName'] != previous['StudentName'] or
                    current['FirstName'] != previous['FirstName'] or
                    current['LastName'] != previous['LastName'] or
                    current['UWNetID'] != previous['UWNetID'] or
                    current['RegID'] != previous['RegID']):

                user = User.objects.update_priority(
                    PersonModel(uwregid=current['RegID'], uwnetid=net_id),
                    User.PRIORITY_HIGH)

                action = 'IGNORE unknown user' if (user is None) else 'ACCEPT'
                self.logger.info('{} {}, uwnetid: {}, uwregid: {}'.format(
                    log_prefix, action, current['UWNetID'], current['RegID']))

                self.record_success_to_log(event_count=1)
            else:
                self.logger.info(
                    '{} IGNORE unchanged, uwnetid: {}, uwregid: {}'.format(
                        log_prefix, current['UWNetID'], current['RegID']))

            self.record_success_to_log(event_count=1)
        else:
            self.logger.info(
                '{} IGNORE missing uwnetid, uwnetid: {}, uwregid: {}'.format(
                    log_prefix, net_id, current['RegID'] if (
                        current) else previous['RegID']))
