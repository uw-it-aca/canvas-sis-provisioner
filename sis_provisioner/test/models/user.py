from django.test import TestCase
from django.db.models.query import QuerySet
from restclients.pws import PWS
from sis_provisioner.models import (
    User, Import, PRIORITY_NONE, PRIORITY_DEFAULT, PRIORITY_HIGH)
from datetime import datetime
import mock


class UserModelTest(TestCase):
    def test_update_priority(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            person = PWS().get_person_by_netid('javerage')
            user = User.objects.add_user(person)
            self.assertEquals(user.priority, PRIORITY_HIGH)

            user = User.objects.update_priority(person, PRIORITY_NONE)
            self.assertEquals(user.priority, PRIORITY_NONE)
            User.objects.all().delete()

    @mock.patch.object(QuerySet, 'update')
    def test_dequeue(self, mock_update):
        dt = datetime.now()
        r = User.objects.dequeue(Import(pk=1,
                                        priority=PRIORITY_HIGH,
                                        canvas_state='imported',
                                        post_status=200,
                                        canvas_progress=100,
                                        monitor_date=dt))
        mock_update.assert_called_with(
            priority=PRIORITY_DEFAULT, queue_id=None, provisioned_date=dt)

        r = User.objects.dequeue(Import(pk=1, priority=PRIORITY_HIGH))
        mock_update.assert_called_with(queue_id=None)

    def test_add_user(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            person = PWS().get_person_by_netid('javerage')
            user = User.objects.add_user(person)
            self.assertEquals(user.reg_id, person.uwregid)
            self.assertEquals(user.net_id, person.uwnetid)
            self.assertEquals(user.priority, PRIORITY_HIGH)
            User.objects.all().delete()

            person = PWS().get_person_by_netid('javerage')
            user = User.objects.add_user(person, priority=PRIORITY_NONE)
            self.assertEquals(user.reg_id, person.uwregid)
            self.assertEquals(user.net_id, person.uwnetid)
            self.assertEquals(user.priority, PRIORITY_NONE)
            User.objects.all().delete()

    def test_json_data(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            person = PWS().get_person_by_netid('javerage')
            user = User.objects.add_user(person)

            json = user.json_data()
            self.assertEquals(json['net_id'], 'javerage')
            self.assertEquals(json['reg_id'], '9136CCB8F66711D5BE060004AC494FFE')
            self.assertEquals(json['queue_id'], None)
            self.assertEquals(json['provisioned_date'], None)
            self.assertEquals(json['priority'], 'high')

            User.objects.all().delete()
