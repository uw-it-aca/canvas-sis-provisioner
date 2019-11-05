from django.conf import settings
from rc_django.cache_implementation import TimedCache
from rc_django.models import CacheEntryTimed
from uw_kws import ENCRYPTION_KEY_URL, ENCRYPTION_CURRENT_KEY_URL
import re


class RestClientsCache(TimedCache):
    """ A custom cache implementation for Canvas """

    url_policies = {}
    url_policies["sws"] = (
        (re.compile(r"^/student/v\d/term/"), 60 * 60 * 10),
        (re.compile(r"^/student/v\d/course/"), 60 * 5),
        (re.compile(r"^/student/v\d/campus"), 60 * 60 * 10),
        (re.compile(r"^/student/v\d/college"), 60 * 60 * 10),
        (re.compile(r"^/student/v\d/department"), 60 * 60 * 10),
    )
    url_policies["pws"] = (
        (re.compile(r"^/identity/v\d/person/"), 60 * 60),
        (re.compile(r"^/identity/v\d/entity/"), 60 * 60),
    )
    url_policies["kws"] = (
        (re.compile(r"{}".format(
            ENCRYPTION_KEY_URL.format(r'[\-\da-fA-F]{36}'))),
            60 * 60 * 24 * 30),
        (re.compile(r"{}".format(
            ENCRYPTION_CURRENT_KEY_URL.format(r"[\-\da-zA-Z]+"))),
            60 * 60 * 24 * 7),
    )
    url_policies["gws"] = (
        (re.compile(r"^/group_sws/v\d/group/{}/effective_member/".format(
            getattr(settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP', 'none'))),
            60 * 60),
    )
    url_policies["canvas"] = (
        (re.compile(r"^/api/v\d/accounts/sis_account_id:"), 60 * 60 * 10),
        (re.compile(r"^/api/v\d/accounts/\d+/roles"), 60 * 60 * 4),
    )
    url_policies["libcurrics"] = (
        (re.compile(r"^/currics_db/api/v\d/data/course/"), 60 * 60 * 4),
    )

    def deleteCache(self, service, url):
        try:
            entry = CacheEntryTimed.objects.get(service=service, url=url)
            entry.delete()
        except CacheEntryTimed.DoesNotExist:
            return

    def delete_cached_kws_current_key(self, resource_type):
        self.deleteCache('kws', ENCRYPTION_CURRENT_KEY_URL.format(
            resource_type))

    def delete_cached_kws_key(self, key_id):
        self.deleteCache('kws', ENCRYPTION_KEY_URL.format(key_id))

    def _get_cache_policy(self, service, url):
        for policy in RestClientsCache.url_policies.get(service, []):
            if policy[0].match(url):
                return policy[1]
        return 0

    def getCache(self, service, url, headers):
        cache_policy = self._get_cache_policy(service, url)
        return self._response_from_cache(service, url, headers, cache_policy)

    def processResponse(self, service, url, response):
        if self._get_cache_policy(service, url):
            return self._process_response(service, url, response)
