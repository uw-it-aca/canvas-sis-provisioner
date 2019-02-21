from django.conf import settings
from suds.client import Client
from suds.transport.http import HttpTransport
from suds import WebFault
from urllib.request import build_opener, HTTPSHandler
from sis_provisioner.exceptions import ASTRAException
import socket
import http
import ssl


class HTTPSConnectionClientCertV3(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        http.client.HTTPSConnection.__init__(self, *args, **kwargs)
        self.key_file = settings.ASTRA_KEY
        self.cert_file = settings.ASTRA_CERT

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ssl_version=ssl.PROTOCOL_TLSv1)
        except ssl.SSLError as err:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ssl_version=ssl.PROTOCOL_SSLv3)


class HTTPSClientAuthHandler(HTTPSHandler):
    def __init__(self):
        HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(HTTPSConnectionClientCertV3, req)

    def getConnection(self, host, timeout=300):
        return HTTPSConnectionClientCertV3(host)


class HTTPSTransportV3(HttpTransport):
    def __init__(self, *args, **kwargs):
        HttpTransport.__init__(self, *args, **kwargs)

    def u2open(self, u2request):
        tm = self.options.timeout
        url = build_opener(HTTPSClientAuthHandler())
        if self.u2ver() < 2.6:
            socket.setdefaulttimeout(tm)
            return url.open(u2request)
        else:
            return url.open(u2request, timeout=tm)


class ASTRA():
    def __init__(self, *args, **kwargs):
        self._client = Client(settings.ASTRA_WSDL,
                              transport=HTTPSTransportV3())

    def _request(self, method_name, params={}):
        try:
            return self._client.service['AuthzProvider'][method_name](params)
        except WebFault as ex:
            raise ASTRAException('ASTRA: Request failed, {}'.format(ex))

    def get_version(self):
        return self._request('GetVersion')

    def get_authz(self):
        auth_filter = self._client.factory.create('authFilter')
        auth_filter.privilege._code = settings.ASTRA_APPLICATION
        auth_filter.environment._code = settings.ASTRA_ENVIRONMENT
        auth_filter.astraRole._code = 'User'

        authz = self._request('GetAuthz', auth_filter)

        if authz.get('authCollection', {}).get('auth') is None:
            raise ASTRAException('ASTRA: Missing authCollection.auth')

        return authz.authCollection.auth
