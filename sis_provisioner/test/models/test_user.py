# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.db.models.query import QuerySet
from uw_pws import PWS
from uw_pws.util import fdao_pws_override
from sis_provisioner.exceptions import UserPolicyException
from sis_provisioner.models import Import
from sis_provisioner.models.user import User
from datetime import datetime
import mock


@fdao_pws_override
class UserModelTest(TestCase):
    def test_update_priority(self):
        person = PWS().get_person_by_netid('javerage')
        user = User.objects.add_user(person)
        self.assertEquals(user.priority, User.PRIORITY_HIGH)

        user = User.objects.update_priority(person, User.PRIORITY_NONE)
        self.assertEquals(user.priority, User.PRIORITY_NONE)
        User.objects.all().delete()

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now()
        r = User.objects.dequeue(Import(pk=1,
                                        priority=User.PRIORITY_HIGH,
                                        canvas_state='imported',
                                        post_status=200,
                                        canvas_progress=100,
                                        monitor_date=dt))
        mock_update.assert_called_with(priority=User.PRIORITY_DEFAULT,
                                       queue_id=None,
                                       provisioned_date=dt)

        r = User.objects.dequeue(Import(pk=1, priority=User.PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)

    def test_add_user(self):
        person = PWS().get_person_by_netid('javerage')
        user = User.objects.add_user(person)
        self.assertEquals(user.reg_id, person.uwregid)
        self.assertEquals(user.net_id, person.uwnetid)
        self.assertEquals(user.priority, User.PRIORITY_HIGH)
        User.objects.all().delete()

        person = PWS().get_person_by_netid('javerage')
        user = User.objects.add_user(person, priority=User.PRIORITY_NONE)
        self.assertEquals(user.reg_id, person.uwregid)
        self.assertEquals(user.net_id, person.uwnetid)
        self.assertEquals(user.priority, User.PRIORITY_NONE)
        User.objects.all().delete()

    def test_add_user_by_netid(self):
        user = User.objects.add_user_by_netid('bill')
        self.assertEquals(user.net_id, 'bill')
        self.assertEquals(user.priority, User.PRIORITY_HIGH)

        user = User.objects.add_user_by_netid('bill',
                                              priority=User.PRIORITY_NONE)
        self.assertEquals(user.net_id, 'bill')
        self.assertEquals(user.priority, User.PRIORITY_NONE)

        # is_test_entity
        self.assertRaises(UserPolicyException, User.objects.add_user_by_netid,
            'javerage')

    def test_json_data(self):
        person = PWS().get_person_by_netid('javerage')
        user = User.objects.add_user(person)

        json = user.json_data()
        self.assertEquals(json['net_id'], 'javerage')
        self.assertEquals(json['reg_id'], '9136CCB8F66711D5BE060004AC494FFE')
        self.assertEquals(json['queue_id'], None)
        self.assertEquals(json['provisioned_date'], None)
        self.assertEquals(json['priority'], 'high')

        User.objects.all().delete()
