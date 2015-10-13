from restclients.cache_implementation import TimedCache
import re


class RestClientsCache(TimedCache):
    """ A custom cache implementation for Canvas """

    url_policies = {}
    url_policies["sws"] = (
        (re.compile(r"^/student/v5/term/"), 60 * 60 * 10),
        (re.compile(r"^/student/v5/course/"), 60 * 5),
    )
    url_policies["pws"] = (
        (re.compile(r"^/identity/v1/person/"), 60 * 60),
        (re.compile(r"^/identity/v1/entity/"), 60 * 60),
        (re.compile(r"^/idcard/v1/photo/"), 60 * 60 * 24 * 7),
    )
    url_policies["canvas"] = (
        (re.compile(r"^/api/v1/accounts/\d+/roles"), 60 * 60 * 4),
    )

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
