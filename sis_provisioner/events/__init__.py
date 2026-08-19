# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import json
import re
from base64 import b64decode
from logging import getLogger
from math import floor
from time import time

from aws_message.crypto import CryptoException, Signature, aes128cbc
from aws_message.processor import MessageBodyProcessor, ProcessorException
from prometheus_client import Counter
from restclients_core.exceptions import DataFailureException
from uw_kws import KWS

from sis_provisioner.cache import RestClientsCache
from sis_provisioner.exceptions import EventException
from sis_provisioner.models.enrollment import Enrollment

logger = getLogger(__name__)
prometheus_canvas_events = Counter(
    'canvas_event_count',
    'Canvas Event Counter',
    ['source'])


class SISProvisionerProcessor(MessageBodyProcessor):
    _re_json_cruft = re.compile(r'[^{]*({.*})[^}]*')

    def __init__(self, queue_settings_name, is_encrypted):
        super().__init__(
                logger, queue_settings_name, is_encrypted=is_encrypted)

    def validate_message_body(self, message):
        header = message.get('Header', {})
        if ('MessageType' in header and
                header['MessageType'] != self._eventMessageType):
            raise ProcessorException(f'Unknown Message Type: {header["MessageType"]}')

        if ('Version' in header and header['Version'] != self._eventMessageVersion):
            raise ProcessorException(f'Unknown Version: {header["Version"]}')

        return True

    def _parse_signature(self, message):
        header = message['Header']
        to_sign = '{msgtype}\n{msgid}\n{timestamp}\n{body}\n'.format(
            msgtype=header['MessageType'], msgid=header['MessageId'],
            timestamp=header['TimeStamp'], body=message['Body'])

        sig_conf = {
            'cert': {
                'type': 'url',
                'reference': header['SigningCertURL']
            }
        }

        return (sig_conf, to_sign, header['Signature'])

    def validate_message_body_signature(self, message):
        try:
            (sig_conf, to_sign, signature) = self._parse_signature(message)
            Signature(sig_conf).validate(to_sign.encode('ascii'), b64decode(signature))

        except KeyError as ex:
            if len(message['Header']):
                raise ProcessorException(f'Invalid Signature Header: {ex}')
        except CryptoException as ex:
            raise ProcessorException(f'Cannot decode message: {ex}')
        except Exception as ex:
            raise ProcessorException(f'Invalid signature {signature}: {ex}')

    def decrypt_message_body(self, message):
        header = message['Header']
        body = message['Body']

        try:
            if 'Encoding' not in header:
                if isinstance(body, str):
                    return json.loads(self._re_json_cruft.sub(r'\g<1>', body))
                elif isinstance(body, dict):
                    return body
                else:
                    raise ProcessorException('No body encoding')

            encoding = header['Encoding']
            if str(encoding).lower() != 'base64':
                raise ProcessorException(f'Unkown encoding: {encoding}')

            algorithm = header.get('Algorithm', 'aes128cbc')
            if str(algorithm).lower() != 'aes128cbc':
                raise ProcessorException(f'Unsupported algorithm: {algorithm}')

            kws = KWS()
            key = None
            if 'KeyURL' in header:
                key = kws.get_key(url=header['KeyURL'])
            elif 'KeyId' in self._header:
                key = kws.get_key(key_id=self._header['KeyId'])
            else:
                try:
                    key = kws.get_current_key(header['MessageType'])
                    if not re.match(r'^\s*{.+}\s*$', body):
                        raise CryptoException()
                except (ValueError, CryptoException):
                    RestClientsCache().delete_cached_kws_current_key(
                        header['MessageType'])
                    key = kws.get_current_key(header['MessageType'])

            cipher = aes128cbc(b64decode(key.key), b64decode(header['IV']))
            body = cipher.decrypt(b64decode(body))

            return json.loads(
                self._re_json_cruft.sub(r'\g<1>', body.decode('utf-8')))

        except KeyError as ex:
            logger.error(f'Key Error: {ex}\nHEADER: {header}')
            raise
        except ValueError as ex:
            logger.error(f'Error: {ex}\nHEADER: {header}\nBODY: {body}')
            return {}
        except CryptoException as ex:
            logger.error(f'Error: {ex}\nHEADER: {header}\nBODY: {body}')
            raise ProcessorException(f'Cannot decrypt: {ex}')
        except DataFailureException as ex:
            msg = f'Request failure for {ex.url}: {ex.msg} ({ex.status})'
            logger.error(msg)
            raise ProcessorException(msg)
        except Exception as ex:
            raise ProcessorException(f'Cannot read: {ex}')

    def load_enrollments(self, enrollments):
        enrollment_count = len(enrollments)
        if enrollment_count:
            for enrollment in enrollments:
                try:
                    Enrollment.objects.add_enrollment(enrollment)
                except Exception as ex:
                    raise ProcessorException(f'Load enrollment failed: {ex}')

            try:
                self.record_success_to_log(event_count=enrollment_count)
            except Exception:
                pass

    def record_success_to_log(self, event_count=0):
        log_model = self._logModel

        if event_count > 0:
            m = re.match(r'^events_(.+)log$', log_model._meta.db_table)
            source = m.group(1) if m else log_model._meta.db_table
            prometheus_canvas_events.labels(source).inc(event_count)

        minute = floor(time() / 60)
        try:
            e = log_model.objects.get(minute=minute)
            e.event_count += event_count
        except log_model.DoesNotExist:
            e = log_model(minute=minute, event_count=event_count)

        e.save()

        if e.event_count <= 5:
            limit = self.settings.get('EVENT_COUNT_PRUNE_AFTER_DAY', 7) * 24 * 60
            prune = minute - limit
            log_model.objects.filter(minute__lt=prune).delete()

    def check_interval(self, acceptable_silence=6*60):
        recent = self._logModel.objects.all().order_by('-minute')[:1]
        if len(recent):
            delta = (floor(time() / 60)) - recent[0].minute
            if (delta > acceptable_silence):
                raise EventException(
                    f'No events in the last {floor(delta / 60)} hours and '
                    f'{delta % 60} minutes'
                )
