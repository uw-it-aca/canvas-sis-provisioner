from sis_provisioner.events import SISProvisionerProcessor, ProcessorException
from sis_provisioner.models.events import GroupLog
from sis_provisioner.events.group.dispatch import (
    ImportGroupDispatch, CourseGroupDispatch, UWGroupDispatch)
from aws_message.crypto import aes128cbc, CryptoException
from base64 import b64decode
import json

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
        super(GroupProcessor, self).__init__(
            queue_settings_name=QUEUE_SETTINGS_NAME)

    def validate_inner_message(self, message):
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
                ImportGroupDispatch, CourseGroupDispatch, UWGroupDispatch]:
            dispatch = dispatch_class(self.settings)
            if dispatch.mine(self._groupname):
                self._dispatch = dispatch
                break

        return (self._dispatch is not None)

    def _parse_signature(self, message):
        header = message['header']
        signature = header['signature']
        to_sign = '{}\n'.format(header[u'contentType'])
        if 'keyId' in header:
            to_sign += '{}\n{}\n'.format(header[u'iv'], header[u'keyId'])
        to_sign += (
            '{context}\n{msgid}\n{msgtype}\n{sender}\n{cert}\n'
            '{timestamp}\n{version}\n{body}\n').format(
            context=header[u'messageContext'], msgid=header[u'messageId'],
            msgtype=header[u'messageType'], sender=header[u'sender'],
            cert=header[u'signingCertUrl'], timestamp=header[u'timestamp'],
            version=header[u'version'], body=message['body'])

        sig_conf = {
            'cert': {
                'type': 'url',
                'reference': header[u'signingCertUrl']
            }
        }

        return (sig_conf, to_sign, signature)

    def decrypt_inner_message(self, message):
        header = message['header']
        body = message['body']
        try:
            if set(['keyId', 'iv']).issubset(header):
                key = header['keyId']
                keys = self.get_payload_settings().get('KEYS', {})

                cipher = aes128cbc(
                    b64decode(keys[key]), b64decode(header['iv']))
                body = cipher.decrypt(b64decode(body))
                return body
                # return json.loads(self._re_json_cruft.sub(r'\g<1>', body))

        except KeyError as ex:
            raise ProcessorException('Invalid keyId: {}'.format(key))
        except CryptoException as ex:
            raise ProcessorException('Cannot decrypt: {}'.format(ex))
        except Exception as ex:
            raise ProcessorException('Cannot read: {}'.format(ex))

    def process_inner_message(self, json_data):
        n = self._dispatch.run(self._action, self._groupname, json_data)
        if n:
            self.record_success_to_log(n)
