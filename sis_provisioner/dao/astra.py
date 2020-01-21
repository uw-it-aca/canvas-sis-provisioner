from django.conf import settings
from suds.client import Client
from suds.transport.http import HttpTransport
from suds import WebFault
from urllib.request import build_opener, HTTPSHandler
from sis_provisioner.dao.account import (
    get_campus_by_label, get_college_by_label, get_department_by_label,
    account_sis_id)
from sis_provisioner.exceptions import ASTRAException
from logging import getLogger
import socket
import http
import ssl
import re

logger = getLogger(__name__)
RE_NONACADEMIC_CODE = re.compile(r'^canvas_([0-9]+)$')


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
        return self._request('GetAuthz', auth_filter)

    def get_canvas_admins(self):
        authz = self.get_authz()

        if not ('authCollection' in authz and 'auth' in authz.authCollection):
            raise ASTRAException('Missing authCollection.auth')

        admins = []
        for auth in authz.authCollection.auth:
            try:
                # Sanity checks
                if auth.role._code not in settings.ASTRA_ROLE_MAPPING:
                    raise ASTRAException('Unknown Role Code {}'.format(
                        auth.role._code))
                if '_regid' not in auth.party:
                    raise ASTRAException('Missing uwregid, {}'.format(
                        auth.party))
                if 'spanOfControlCollection' not in auth:
                    raise ASTRAException('Missing SpanOfControl, {}'.format(
                        auth.party))

                collection = auth.spanOfControlCollection
                if ('spanOfControl' in collection and
                        isinstance(collection.spanOfControl, list)):
                    soc = collection.spanOfControl[0]
                    if soc._type.lower() == 'swscampus':
                        # Academic subaccount
                        sis_id = self._canvas_account_from_academic_soc(
                            collection.spanOfControl)
                        canvas_id = None
                    else:
                        # Ad-hoc subaccount
                        sis_id = None
                        canvas_id = self._canvas_id_from_nonacademic_soc(
                            soc._code)
                else:
                    # Root account
                    sis_id = None
                    canvas_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
            except ASTRAException as err:
                logger.error('ASTRA Data Error: {}'.format(err))
                continue

            admins.append({
                'net_id': auth.party._uwNetid,
                'reg_id': auth.party._regid,
                'account_sis_id': sis_id,
                'canvas_id': canvas_id,
                'role': auth.role._code
            })

        return admins

    @staticmethod
    def _canvas_id_from_nonacademic_soc(code):
        m = RE_NONACADEMIC_CODE.match(code)
        if m is not None:
            return m.group(1)
        raise ASTRAException('Unknown Non-Academic Code: {}'.format(code))

    @staticmethod
    def _canvas_account_from_academic_soc(soc):
        id_parts = []
        campus = None
        college = None
        for item in soc:
            itype = item._type.lower()
            if itype == 'swscampus':
                id_parts.append(settings.SIS_IMPORT_ROOT_ACCOUNT_ID)
                campus = get_campus_by_label(item._code)
                try:
                    id_parts.append(campus.label)
                except AttributeError:
                    raise ASTRAException('Unknown Campus: {}'.format(item))

            elif itype == 'swscollege':
                if campus is None:
                    raise ASTRAException('Missing Campus, {}'.format(item))
                college = get_college_by_label(campus, item._code)
                try:
                    id_parts.append(college.name)
                except AttributeError:
                    raise ASTRAException('Unknown College: {}'.format(item))

            elif itype == 'swsdepartment':
                if campus is None or college is None:
                    raise ASTRAException('Missing College, {}'.format(item))
                dept = get_department_by_label(college, item._code)
                try:
                    id_parts.append(dept.label)
                except AttributeError:
                    raise ASTRAException('Unknown Department: {}'.format(item))

            else:
                raise ASTRAException('Unknown SoC type, {}'.format(item))

        if not len(id_parts):
            raise ASTRAException('SoC empty list')

        return account_sis_id(id_parts)
