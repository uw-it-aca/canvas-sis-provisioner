import re
import json
from django.utils.log import getLogger
from restclients.sws import SWS
from sis_provisioner.models import PRIORITY_NONE
from sis_provisioner.models import Enrollment
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views import regid_from_request, netid_from_request
from sis_provisioner.policy import UserPolicy
from restclients.pws import PWS


class EnrollmentInvalidException(Exception):
    pass


class EnrollmentListView(RESTDispatch):
    """ Retrieves a list of Enrollments at /api/v1/enrollments/?<criteria[&criteria]>.
        GET returns 200 with Enrollment details.
    """
    def __init__(self):
        self._sws = SWS()
        self._pws = PWS()
        self._criteria = [
            {
                'term': 'year',
                'test': re.compile(r'^\d{4}$').match,
                'required': True
            },
            {
                'term': 'quarter',
                'test': re.compile(r'^(?:winter|spring|summer|autumn)+$', re.I).match,
                'required': True,
                'case': 'lower'
            },
            {
                'term': 'curriculum_abbreviation',
                'test': re.compile(r'^[a-z &]+$', re.I).match,
                'case': 'upper'
            },
            {
                'term': 'course_number',
                'test': re.compile(r'^\d{3}$').match,
            },
            {
                'term': 'section',
                'test': re.compile(r'^[a-z]{1,2}$', re.I).match,
                'case': 'upper'
            }
        ]
        self._log = getLogger(__name__)
        self._user_policy = UserPolicy()

    def GET(self, request, **kwargs):
        json_rep = {
            'enrollments': []
        }

        filt_kwargs = None

        if 'queue_id' in request.GET:
            queue_id = request.GET.get('queue_id', '').strip()
            if re.match(r'^[0-9]+$', str(queue_id)):
                filt_kwargs = {'queue_id': queue_id}
            else:
                errstr = 'invalid queue_id: %s' % queue_id
                self._log.error(errstr)
                return self.json_response('{"error":"%s"}' % errstr, status=400)
        else:
            provisioned_error = request.GET.get('provisioned_error')
            if provisioned_error:
                filt_kwargs = {'provisioned_error': True if self._is_true(provisioned_error) else None,
                               'queue_id__isnull': True}

        if filt_kwargs:
            try:
                filt_kwargs['priority__gt'] = PRIORITY_NONE
                enrollment_list = list(Enrollment.objects.filter(**filt_kwargs))
                for enrollment in enrollment_list:
                    json_rep['enrollments'].append(enrollment.json_data())

                return self.json_response(json.dumps(json_rep))
            except Exception, err:
                self._log.error('enrollment kwargs search fail: ' + str(err))
                return self.json_response('{"error":"' + str(err) + '"}', status=400)

        reg_id = None
        try:
            if 'net_id' in request.GET:
                reg_id = self._pws.get_person_by_netid(netid_from_request(request.GET)).uwregid
            elif 'reg_id' in request.GET:
                reg_id = regid_from_request(request.GET)
            else:
                self._criteria[2]['required'] = True

            filter_terms = self._validEnrollmentFilter(request)
            filter_prefix = '-'.join(filter_terms)
            enrollment_list = list(Enrollment.objects.filter(course_id__startswith=filter_prefix,
                                                             reg_id=reg_id))
        except EnrollmentInvalidException, err:
            return self.json_response('{"error":"' + str(err) + '"}', status=400)
        except Exception, err:
            self._log.error('course filter fail: ' + str(err))
            return self.json_response('{"error":"' + str(err) + '"}', status=400)

        return self.json_response(json.dumps(json_rep))

    def _validEnrollmentFilter(self, request):
        values = []
        for filter in self._criteria:
            value = request.GET.get(filter['term'], '').strip()
            if value is None or not len(value):
                if 'required' in filter and filter['required'] is True:
                    raise EnrollmentInvalidException(filter['term'] + ' query term is required')
                else:
                    break
            elif filter['test'](value):
                if 'case' in filter:
                    if filter['case'] == 'upper':
                        value = value.upper()
                    else:
                        value = value.lower()

                values.append(value)
            else:
                raise EnrollmentInvalidException(filter['term'] + ' is invalid')

        return values

    def _is_true(self, val):
        return True if (val == '1' or re.match(r'^(yes|true)$', val, re.I)) else False

