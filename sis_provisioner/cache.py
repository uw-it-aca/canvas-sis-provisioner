# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from memcached_clients import RestclientPymemcacheClient
from uw_kws import ENCRYPTION_KEY_URL, ENCRYPTION_CURRENT_KEY_URL
import re

ONE_MINUTE = 60
ONE_HOUR = 60 * 60
ONE_DAY = 60 * 60 * 24
ONE_WEEK = 60 * 60 * 24 * 7
ONE_MONTH = 60 * 60 * 24 * 30
NONPERSONAL_NETID_EXCEPTION_GROUP = getattr(
    settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP', 'none')


class RestClientsCache(RestclientPymemcacheClient):
    def get_cache_expiration_time(self, service, url, status=200):
        if 'sws' == service:
            if re.match(r'^/student/v\d/course/', url):
                return ONE_MINUTE * 5
            if re.match(r'^/student/v\d/term/', url):
                return ONE_HOUR * 4
            if re.match(
                r'^/student/v\d/(?:campus|college|department|curriculum)',
                    url):
                return ONE_HOUR * 4

        if 'pws' == service:
            return ONE_HOUR

        if 'kws' == service:
            if re.search(r'{}'.format(
                    ENCRYPTION_KEY_URL.format(r'[\-\da-fA-F]{36}')), url):
                return ONE_MONTH
            if re.search(r'{}'.format(
                    ENCRYPTION_CURRENT_KEY_URL.format(r'[\-\da-zA-Z]+')), url):
                return ONE_WEEK

        if 'gws' == service:
            if re.match(r'^/group_sws/v\d/group/u_somalt_', url):
                return ONE_HOUR

            if re.match(r'^/group_sws/v\d/group/{}/effective_member/'.format(
                    NONPERSONAL_NETID_EXCEPTION_GROUP), url):
                return ONE_HOUR

        if 'canvas' == service:
            if re.match(r'^/api/v\d/accounts/sis_account_id:', url):
                return ONE_HOUR * 10
            if re.match(r'^/api/v\d/accounts/\d+/roles', url):
                return ONE_MONTH

    def delete_cached_kws_current_key(self, resource_type):
        self.deleteCache('kws', ENCRYPTION_CURRENT_KEY_URL.format(
            resource_type))
