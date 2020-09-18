from django.conf import settings
from rc_django.cache_implementation import TimedCache
from rc_django.cache_implementation.memcache import MemcachedCache
from uw_kws import ENCRYPTION_KEY_URL, ENCRYPTION_CURRENT_KEY_URL
import re

ONE_MINUTE = 60
ONE_HOUR = 60 * 60
ONE_DAY = 60 * 60 * 24
ONE_WEEK = 60 * 60 * 24 * 7
ONE_MONTH = 60 * 60 * 24 * 30
NONPERSONAL_NETID_EXCEPTION_GROUP = getattr(
    settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP', 'none')


def get_cache_time(service, url):
    if 'sws' == service:
        if re.match(r'^/student/v\d/course/', url):
            return ONE_MINUTE * 5
        if re.match(r'^/student/v\d/(?:campus|college|department|term)', url):
            return ONE_HOUR * 10

    if 'pws' == service:
        if re.match(r'^/identity/v\d/', url):
            return ONE_HOUR

    if 'kws' == service:
        if re.match(r'{}'.format(
                ENCRYPTION_KEY_URL.format(r'[\-\da-fA-F]{36}')), url):
            return ONE_MONTH
        if re.match(r'{}'.format(
                ENCRYPTION_CURRENT_KEY_URL.format(r'[\-\da-zA-Z]+')), url):
            return ONE_WEEK

    if 'gws' == service:
        if re.match(r'^/group_sws/v\d/group/{}/effective_member/'.format(
                NONPERSONAL_NETID_EXCEPTION_GROUP), url):
            return ONE_HOUR

    if 'canvas' == service:
        if re.match(r'^/api/v\d/accounts/sis_account_id:', url):
            return ONE_HOUR * 10
        if re.match(r'^/api/v\d/accounts/\d+/roles', url):
            return ONE_WEEK

    if 'libcurrics' == service:
        return ONE_HOUR * 4


class CanvasMemcachedCache(MemcachedCache):
    def get_cache_expiration_time(self, service, url):
        return get_cache_time(service, url)

    def delete_cached_kws_current_key(self, resource_type):
        self.deleteCache('kws', ENCRYPTION_CURRENT_KEY_URL.format(
            resource_type))

    def delete_cached_kws_key(self, key_id):
        self.deleteCache('kws', ENCRYPTION_KEY_URL.format(key_id))


class RestClientsCache(TimedCache):
    """ A custom cache implementation for Canvas """
    def delete_cached_kws_current_key(self, resource_type):
        self.deleteCache('kws', ENCRYPTION_CURRENT_KEY_URL.format(
            resource_type))

    def delete_cached_kws_key(self, key_id):
        self.deleteCache('kws', ENCRYPTION_KEY_URL.format(key_id))

    def getCache(self, service, url, headers):
        return self._response_from_cache(
            service, url, headers, get_cache_time(service, url))

    def processResponse(self, service, url, response):
        if get_cache_time(service, url):
            return self._process_response(service, url, response)
