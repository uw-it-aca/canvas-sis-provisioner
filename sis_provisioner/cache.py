from django.conf import settings
from rc_django.cache_implementation import TimedCache
from rc_django.models import CacheEntryTimed
import re


class RestClientsCache(TimedCache):
    """ A custom cache implementation for Canvas """

    canvas_url_roles = '/api/v1/accounts/%s/roles'
    kws_url_current_key = '/key/v1/type/%s/encryption/current'
    kws_url_key = '/key/v1/encryption/%s.json'

    url_policies = {}
    url_policies["sws"] = (
        (re.compile(r"^/student/v5/term/"), 60 * 60 * 10),
        (re.compile(r"^/student/v5/course/"), 60 * 5),
    )
    url_policies["pws"] = (
        (re.compile(r"^/identity/v1/person/"), 60 * 60),
        (re.compile(r"^/identity/v1/entity/"), 60 * 60),
    )
    url_policies["kws"] = (
        (re.compile(r"^%s" % (
            kws_url_key % '[\-\da-fA-F]{36}\\')), 60 * 60 * 24 * 30),
        (re.compile(r"^%s" % (
            kws_url_current_key % "[\-\da-zA-Z]+")), 60 * 60 * 24 * 7),
    )
    url_policies["gws"] = (
        (re.compile(r"^/group_sws/v2/group/%s/effective_member/" % (
            getattr(settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP', 'none'))),
            60 * 60),
    )
    url_policies["canvas"] = (
        (re.compile(r"^%s" % (canvas_url_roles % '\d+')), 60 * 60 * 4),
    )
    url_policies["libcurrics"] = (
        (re.compile(r"^/currics_db/api/v1/data/course/"), 60 * 60 * 4),
    )

    def deleteCache(self, service, url):
        try:
            entry = CacheEntryTimed.objects.get(service=service, url=url)
            entry.delete()
        except CacheEntryTimed.DoesNotExist:
            return

    def delete_cached_kws_current_key(self, resource_type):
        self.deleteCache('kws', self.kws_url_current_key % resource_type)

    def delete_cached_kws_key(self, key_id):
        self.deleteCache('kws', self.kws_url_key % key_id)

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
