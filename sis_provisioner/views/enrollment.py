# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import re
from logging import getLogger
from sis_provisioner.models.enrollment import Enrollment
from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.user import get_person_by_netid

logger = getLogger(__name__)


class EnrollmentInvalidException(Exception):
    pass


class EnrollmentListView(RESTDispatch):
    """ Retrieves a list of Enrollments at
        /api/v1/enrollments/?<criteria[&criteria]>.
        GET returns 200 with Enrollment details.
    """
    def __init__(self):
        self._criteria = [
            {
                'term': 'year',
                'test': re.compile(r'^\d{4}$').match,
                'required': True
            },
            {
                'term': 'quarter',
                'test': re.compile(
                    r'^(?:winter|spring|summer|autumn)+$', re.I).match,
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

    def get(self, request, *args, **kwargs):
        json_rep = {
            'enrollments': []
        }

        filt_kwargs = None

        if 'queue_id' in request.GET:
            queue_id = request.GET.get('queue_id', '').strip()
            if re.match(r'^[0-9]+$', str(queue_id)):
                filt_kwargs = {'queue_id': queue_id}
            else:
                err = 'invalid queue_id: %s' % queue_id
                logger.error(err)
                return self.error_response(400, err)
        else:
            provisioned_error = request.GET.get('provisioned_error')
            if provisioned_error:
                filt_kwargs = {
                    'provisioned_error': self._is_true(provisioned_error),
                    'queue_id__isnull': True
                }

        if filt_kwargs:
            try:
                filt_kwargs['priority__gt'] = Enrollment.PRIORITY_NONE
                enrollments = list(Enrollment.objects.filter(**filt_kwargs))
                for enrollment in enrollments:
                    json_rep['enrollments'].append(enrollment.json_data())

                return self.json_response(json_rep)
            except Exception as err:
                logger.error('enrollment kwargs search fail: %s' % err)
                return self.error_response(400, err)

        reg_id = None
        try:
            if 'net_id' in request.GET:
                person = get_person_by_netid(
                    self.netid_from_request(request.GET))
                reg_id = person.uwregid
            elif 'reg_id' in request.GET:
                reg_id = self.regid_from_request(request.GET)
            else:
                self._criteria[2]['required'] = True

            filter_terms = self._valid_enrollment_filter(request)
            filter_prefix = '-'.join(filter_terms)
            enrollment_list = list(Enrollment.objects.filter(
                course_id__startswith=filter_prefix, reg_id=reg_id))

        except EnrollmentInvalidException as err:
            return self.error_response(400, err)
        except Exception as err:
            logger.error('course filter fail: %s' % err)
            return self.error_response(400, err)

        return self.json_response(json_rep)

    def _valid_enrollment_filter(self, request):
        values = []
        for filter in self._criteria:
            value = request.GET.get(filter['term'], '').strip()
            if value is None or not len(value):
                if 'required' in filter and filter['required'] is True:
                    raise EnrollmentInvalidException(
                        '%s query term is required' % filter['term'])
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
                raise EnrollmentInvalidException('%s is invalid' % (
                    filter['term']))

        return values

    def _is_true(self, val):
        return True if (
            val == '1' or re.match(r'^(yes|true)$', val, re.I)) else False
