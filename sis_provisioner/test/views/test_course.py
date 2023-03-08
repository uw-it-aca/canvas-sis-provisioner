# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.auth.models import User as DjangoUser
from django.contrib.sessions.middleware import SessionMiddleware
from sis_provisioner.models.course import Course
from sis_provisioner.models.user import User
from sis_provisioner.views.course import CourseView
from sis_provisioner.views.course.expiration import CourseExpirationView
from sis_provisioner.test.models.test_account import create_account
from sis_provisioner.test.models.test_admin import create_admin
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from uw_gws.utilities import fdao_gws_override
from datetime import datetime
import mock


@fdao_pws_override
@fdao_sws_override
@fdao_gws_override
@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID=123,
    RESTCLIENTS_ADMIN_GROUP='u_test_group',
    CANVAS_MANAGER_ADMIN_GROUP='u_acadev_unittest',
    MOCK_SAML_ATTRIBUTES={
        'uwnetid': ['javerage'],
        'isMemberOf': ['u_test_group', 'u_acadev_unittest']})
class CoursevViewTest(TestCase):
    def setUp(self):
        account = create_account(123, 'test1')
        self.admin = create_admin('javerage', account)

        self.user = User(net_id='javerage',
                         reg_id='9136CCB8F66711D5BE060004AC494FFE')
        self.user.save()

        self.course = Course(course_id='2013-summer-TRAIN-101-A',
                             canvas_course_id='123456789')
        self.course.save()

        self.adhoc_course = Course(canvas_course_id='987654321')
        self.adhoc_course.save()

    def test_course_get(self):
        args = ()
        kwargs = {'course_id': self.course.course_id}

        request = RequestFactory().get(
            reverse('CourseInfo', kwargs=kwargs),
            HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(request)
        request.user = DjangoUser.objects.create_user(username='javerage')
        request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        request.session.save()

        response = CourseView.as_view()(request, *args, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_adhoc_course_get(self):
        args = ()
        kwargs = {'course_id': self.adhoc_course.canvas_course_id}

        request = RequestFactory().get(
            reverse('CourseInfo', kwargs=kwargs),
            HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(request)
        request.user = DjangoUser.objects.create_user(username='javerage')
        request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        request.session.save()

        response = CourseView.as_view()(request, *args, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_course_expiration_get(self):
        args = ()
        kwargs = {'course_id': self.course.course_id}

        request = RequestFactory().get(
            reverse('CourseExpiration', kwargs=kwargs),
            HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(request)
        request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        request.session.save()

        response = CourseExpirationView.as_view()(request, *args, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_course_expiration_put(self):
        args = ()
        kwargs = {'course_id': self.course.canvas_course_id}

        request = RequestFactory().put(
            reverse('CourseExpiration', kwargs=kwargs),
            data='{}',
            HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(request)
        request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        request.session.save()

        response = CourseExpirationView.as_view()(request, *args, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_course_expiration_delete(self):
        args = ()
        kwargs = {'course_id': self.course.canvas_course_id}

        request = RequestFactory().delete(
            reverse('CourseExpiration', kwargs=kwargs),
            HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(request)
        request.session['samlUserdata'] = settings.MOCK_SAML_ATTRIBUTES
        request.session.save()

        response = CourseExpirationView.as_view()(request, *args, **kwargs)
        self.assertEqual(response.status_code, 200)
