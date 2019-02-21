from django.conf import settings
from sis_provisioner.models import Admin
from sis_provisioner.dao.astra import ASTRA
from sis_provisioner.dao.account import (
    get_all_campuses, get_all_colleges, get_departments_by_college,
    account_sis_id)
from sis_provisioner.dao.canvas import get_account_by_sis_id
from sis_provisioner.exceptions import ASTRAException
import re

RE_NONACADEMIC_CODE = re.compile(r'^canvas_([0-9]+)$')


class Admins():
    """Load admin table with ASTRA-defined administrators
    """
    def __init__(self, options={}):
        self._departments = {}
        self._canvas_ids = {}

    def _campus_from_code(self, code):
        if not hasattr(self, '_campuses'):
            self._campuses = get_all_campuses()

        for campus in self._campuses:
            if campus.label.lower() == code.lower():
                return campus

        raise ASTRAException('Unknown Campus Code: {}'.format(code))

    def _college_from_code(self, campus, code):
        if not hasattr(self, '_colleges'):
            self._colleges = get_all_colleges()

        for college in self._colleges:
            if (campus.label.lower() == college.campus_label.lower() and
                    code.lower() == college.label.lower()):
                return college

        raise ASTRAException('Unknown College Code: {}'.format(code))

    def _department_from_code(self, college, code):
        if college.label not in self._departments:
            self._departments[college.label] = get_departments_by_college(
                college)

        for department in self._departments[college.label]:
            if department.label.lower() == code.lower():
                return department

        raise ASTRAException('Unknown Department Code: {}'.format(code))

    @staticmethod
    def _canvas_id_from_nonacademic_code(code):
        return RE_NONACADEMIC_CODE.match(code).group(1)

    def canvas_account_from_astra_soc(self, soc):
        id_parts = []
        campus = None
        college = None
        for item in soc:
            _type = item._type
            _code = item._code

            if (_type == 'CanvasNonAcademic' or
                    _type == 'CanvasTestAccount'):
                return (_code, self._canvas_id_from_nonacademic_code(_code))

            elif _type == 'SWSCampus':
                campus = self._campus_from_code(_code)
                id_parts.append(settings.SIS_IMPORT_ROOT_ACCOUNT_ID)
                id_parts.append(campus.label)

            elif _type == 'swscollege':
                if campus is None:
                    raise ASTRAException('Missing campus, {}'.format(item))
                college = self._college_from_code(campus, _code)
                id_parts.append(college.name)

            elif _type == 'swsdepartment':
                if campus is None or college is None:
                    raise ASTRAException('Missing college, {}'.format(item))
                dept = self._department_from_code(college, _code)
                id_parts.append(dept.label)

            else:
                raise ASTRAException('Unknown SoC type, {}'.format(item))

        if not len(id_parts):
            raise ASTRAException('SoC empty list')

        sis_id = account_sis_id(id_parts)

        if sis_id not in self._canvas_ids:
            canvas_account = get_account_by_sis_id(sis_id)
            self._canvas_ids[sis_id] = canvas_account.account_id

        return (sis_id, self._canvas_ids[sis_id])

    def load_all_admins(self, queue_id, options={}):
        authz = ASTRA().get_authz()

        Admin.objects.start_reconcile(queue_id)

        for auth in authz.authCollection.auth:
            # Sanity checks
            if auth.role._code not in settings.ASTRA_ROLE_MAPPING:
                raise ASTRAException('Unknown Role Code {}'.format(
                    auth.role._code))
            if '_regid' not in auth.party:
                raise ASTRAException('Missing uwregid, {}'.format(auth.party))
            if 'spanOfControlCollection' not in auth:
                raise ASTRAException('Missing SpanOfControl, {}'.format(
                    auth.party))

            socc = auth.spanOfControlCollection
            if ('spanOfControl' in socc and
                    isinstance(socc.spanOfControl, list)):
                (account_id, canvas_id) = self.canvas_account_from_astra_soc(
                    socc.spanOfControl)
            else:
                canvas_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
                account_id = 'canvas_{}'.format(canvas_id)

            Admin.objects.add_admin(net_id=auth.party._uwNetid,
                                    reg_id=auth.party._regid,
                                    account_id=account_id,
                                    canvas_id=canvas_id,
                                    role=auth.role._code,
                                    queue_id=queue_id)

        Admin.objects.finish_reconcile(queue_id)


def verify_canvas_admin(admin, canvas_account_id):
    # Create a reverse lookup for ASTRA role, based on the admin role in Canvas
    roles = {v: k for k, v in settings.ASTRA_ROLE_MAPPING.items()}

    # Verify whether this role is ASTRA-defined
    if Admin.objects.has_role_in_account(
            admin.user.login_id, canvas_account_id, roles.get(admin.role)):
        return True

    # Otherwise, verify whether this is a valid ancillary role
    for parent_role, data in settings.ANCILLARY_CANVAS_ROLES.items():
        if 'root' == data['account']:
            ancillary_account_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID
        else:
            ancillary_account_id = canvas_account_id

        if (ancillary_account_id == canvas_account_id and
                data['canvas_role'] == admin.role):
            if Admin.objects.has_role(
                    admin.user.login_id, roles.get(parent_role)):
                return True

    return False
