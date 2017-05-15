import re
import json
from logging import getLogger
from sis_provisioner.dao.course import (
    get_sections_by_instructor_and_term, valid_academic_course_sis_id,
    valid_adhoc_course_sis_id)
from sis_provisioner.dao.term import get_term_by_year_and_quarter
from sis_provisioner.dao.user import get_person_by_netid, get_person_by_regid
from sis_provisioner.models import (
    Course, Group, PRIORITY_NONE, PRIORITY_CHOICES)
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.views import regid_from_request, netid_from_request
from sis_provisioner.views.admin import can_view_source_data
from sis_provisioner.exceptions import CoursePolicyException


class CourseInvalidException(Exception):
    pass


class CourseView(RESTDispatch):
    """ Performs actions on a Course at /api/v1/course/<course id>.
        GET returns 200 with Course details.
        PUT returns 200 and updates the Course information.
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        try:
            course = Course.objects.get(
                course_id=self._normalize(kwargs['course_id']))
            json_data = course.json_data(can_view_source_data())
            return self.json_response(json.dumps(json_data))

        except Exception as err:
            return self.json_response(
                '{"error":"Course not found (%s)"}' % err, status=404)

    def PUT(self, request, **kwargs):
        try:
            course = Course.objects.get(
                course_id=self._normalize(kwargs['course_id']))
        except Exception as err:
            return self.json_response(
                '{"error":"Course not found (%s)"}' % err, status=404)

        if course.queue_id is not None:
            return self.json_response(
                '{"error":"Course already being provisioned"}', status=409)

        body = request.read()
        try:
            new_values = json.loads(body)
        except Exception as err:
            return self.json_response(
                '{"error":"Unable to parse JSON (%s)" }' % err, status=400)

        try:
            # only priority PUTable right now
            param = new_values.get('priority', '').lower()
            new_priority = None
            for key, val in dict(PRIORITY_CHOICES).iteritems():
                if val == param:
                    new_priority = key
                    break

            if new_priority is not None:
                course.priority = new_priority
                course.save()
            else:
                raise Exception("Invalid priority: '%s'" % param)

            json_data = course.json_data(can_view_source_data())
            return self.json_response(json.dumps(json_data))
        except Exception as err:
            return self.json_response('{"error":"%s"}' % err, status=400)

    def _normalize(self, course):
        """ normalize course id case
        """
        course = course.strip()
        try:
            valid_academic_course_sis_id(course)
        except CoursePolicyException:
            try:
                valid_adhoc_course_sis_id(course.lower())
                return course.lower()
            except CoursePolicyException:
                pass

        return course


class CourseListView(RESTDispatch):
    """ Retrieves a list of Courses at /api/v1/courses/?<criteria[&criteria]>.
        GET returns 200 with Course details.
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
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        json_rep = {
            'courses': []
        }

        filt_kwargs = None

        if 'queue_id' in request.GET:
            queue_id = request.GET.get('queue_id', '').strip()
            if re.match(r'^[0-9]+$', str(queue_id)):
                filt_kwargs = {'queue_id': queue_id}
            else:
                err = 'invalid queue_id: %s' % queue_id
                self._log.error(err)
                return self.json_response('{"error":"%s"}' % err, status=400)
        else:
            provisioned_error = request.GET.get('provisioned_error')
            if provisioned_error:
                filt_kwargs = {
                    'provisioned_error': self._is_true(provisioned_error),
                    'queue_id__isnull': True
                }

        if filt_kwargs:
            try:
                filt_kwargs['priority__gt'] = PRIORITY_NONE
                course_list = list(Course.objects.filter(
                    **filt_kwargs).order_by('course_id'))

                include_sws_url = can_view_source_data()
                for course in course_list:
                    json_data = course.json_data(include_sws_url)
                    json_rep['courses'].append(json_data)

                return self.json_response(json.dumps(json_rep))
            except Exception as err:
                self._log.error('course kwargs search fail: %s' + err)
                return self.json_response('{"error":"%s"}' % err, status=400)

        net_id = None
        reg_id = None
        try:
            if 'net_id' in request.GET:
                net_id = netid_from_request(request.GET)
            elif 'reg_id' in request.GET:
                reg_id = regid_from_request(request.GET)
            else:
                self._criteria[2]['required'] = True

            filter_terms = self._validCourseFilter(request)
            filter_prefix = '-'.join(filter_terms)
            course_list = list(Course.objects.filter(
                course_id__startswith=filter_prefix).order_by('course_id'))
        except CourseInvalidException as err:
            return self.json_response('{"error":"%s"}' % err, status=400)
        except Exception as err:
            self._log.error('course filter fail: %s' % err)
            return self.json_response('{"error":"%s"}' % err, status=400)

        if (net_id is not None or reg_id is not None) and len(course_list):
            try:
                if net_id is not None:
                    instructor = get_person_by_netid(net_id)
                else:
                    instructor = get_person_by_regid(reg_id)

                year = request.GET.get('year')
                quarter = request.GET.get('quarter')
                term = get_term_by_year_and_quarter(year, quarter)

                white_list = []
                for section in get_sections_by_instructor_and_term(
                        instructor, term):
                    white_list.append('-'.join([
                        section.term.canvas_sis_id(),
                        section.curriculum_abbr.upper(),
                        section.course_number,
                        section.section_id.upper()]))

            except Exception as err:
                self._log.error('section search fail: %s' % err)
                return self.json_response('{"error":"%s"}' % err, status=400)

        include_sws_url = can_view_source_data()
        for course in course_list:
            if 'white_list' in locals() and course.course_id not in white_list:
                continue

            json_data = course.json_data(include_sws_url)
            json_rep['courses'].append(json_data)

        return self.json_response(json.dumps(json_rep))

    def _validCourseFilter(self, request):
        values = []
        for filter in self._criteria:
            value = request.GET.get(filter['term'], '').strip()
            if value is None or not len(value):
                if 'required' in filter and filter['required'] is True:
                    raise CourseInvalidException(
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
                raise CourseInvalidException('%s is invalid' % filter['term'])

        return values

    def _is_true(self, val):
        return True if (
            val == '1' or re.match(r'^(yes|true)$', val, re.I)) else False
