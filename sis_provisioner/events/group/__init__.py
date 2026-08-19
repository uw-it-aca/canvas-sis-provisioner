# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import json
from base64 import b64decode

from aws_message.crypto import CryptoException, aes128cbc

from sis_provisioner.events import ProcessorException, SISProvisionerProcessor
from sis_provisioner.events.group.dispatch import (
    AffiliateLoginGroupDispatch,
    SponsoredLoginGroupDispatch,
    StudentLoginGroupDispatch,
    UWGroupDispatch,
)
from sis_provisioner.models.events import GroupLog

QUEUE_SETTINGS_NAME = 'GROUP'


class GroupProcessor(SISProvisionerProcessor):
    """
    UW GWS Group Event Processor
    """
    _logModel = GroupLog

    # What we expect in a UW Group event message
    _eventMessageType = 'gws'
    _eventMessageVersion = 'UWIT-1'

    def __init__(self):
        super().__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME, is_encrypted=True)

    def validate_message_body(self, message):
        header = message['header']
        if header['messageType'] != self._eventMessageType:
            raise ProcessorException(
                'Unknown Message Type: {}'.format(header['messageType']))

        if header['version'] != self._eventMessageVersion:
            raise ProcessorException(
                'Unknown Message Version: {}'.format(header['version']))

        context = json.loads(b64decode(header['messageContext']))
        self._action = context['action']
        self._groupname = context['group']
        self._dispatch = None

        for dispatch_class in [
                StudentLoginGroupDispatch, SponsoredLoginGroupDispatch,
                AffiliateLoginGroupDispatch, UWGroupDispatch]:
            dispatch = dispatch_class(self.settings)
            if dispatch.mine(self._groupname):
                self._dispatch = dispatch
                break

        return (self._dispatch is not None)

    def _parse_signature(self, message):
        header = message['header']

        to_sign = '{}\n'.format(header['contentType'])
        if 'keyId' in header:
            to_sign += '{}\n{}\n'.format(header['iv'], header['keyId'])
        to_sign += (
            '{context}\n{msgid}\n{msgtype}\n{sender}\n{cert}\n'
            '{timestamp}\n{version}\n{body}\n').format(
            context=header['messageContext'], msgid=header['messageId'],
            msgtype=header['messageType'], sender=header['sender'],
            cert=header['signingCertUrl'], timestamp=header['timestamp'],
            version=header['version'], body=message['body'])

        sig_conf = {
            'cert': {
                'type': 'url',
                'reference': header['signingCertUrl']
            }
        }

        return (sig_conf, to_sign, header['signature'])

    def decrypt_message_body(self, message):
        header = message['header']
        body = message['body']
        try:
            if {'keyId', 'iv'}.issubset(header):
                key = header['keyId']
                keys = self.settings.get('BODY_DECRYPT_KEYS', {})

                cipher = aes128cbc(
                    b64decode(keys[key]), b64decode(header['iv']))
                body = cipher.decrypt(b64decode(body))
                return body

        except KeyError:
            raise ProcessorException(f'Invalid keyId: {key}')
        except CryptoException as ex:
            raise ProcessorException(f'Cannot decrypt: {ex}')
        except Exception as ex:
            raise ProcessorException(f'Cannot read: {ex}')

    def process_message_body(self, json_data):
        if json_data is not None:
            n = self._dispatch.run(self._action, self._groupname, json_data)
            if n:
                self.record_success_to_log(n)
