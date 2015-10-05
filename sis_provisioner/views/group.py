import re
import json
import datetime
from django.utils.timezone import utc
from django.http import HttpResponse
from django.utils.log import getLogger
from django.core.exceptions import ValidationError
from sis_provisioner.models import Course, Group, GroupMemberGroup
from sis_provisioner.models import PRIORITY_NONE, PRIORITY_IMMEDIATE
from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.policy import GroupPolicy, GroupPolicyException
from sis_provisioner.policy import CoursePolicy, CoursePolicyException
from blti import BLTI, BLTIException


class GroupInvalidException(Exception):
    pass


class GroupView(RESTDispatch):
    """ Exposes Group model
        GET returns Group details
        POST inserts new Group
        DELETE removes Group
    """
    def __init__(self):
        self._course_policy = CoursePolicy()
        self._group_policy = GroupPolicy()
        self._re_id = re.compile(r'^[0-9]+$')
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        try:
            self._blti = BLTI().get_session(request)
        except BLTIException:
            return self.json_response(content="Unauthorized", status=401)

        id = kwargs.get('id')
        if id is not None:
            course_id = self._course_policy.adhoc_sis_id(id)
            return self._getGroupById(course_id)
        else:
            return self._getGroupsByQuery(request)

    def POST(self, request, **kwargs):
        try:
            self._blti = BLTI().get_session(request)
        except BLTIException:
            return self.json_response(content="Unauthorized", status=401)

        try:
            post_json = json.loads(request.read())
            course_id, canvas_id, group_id, role = self._validate_post(post_json)
            user_id = self._blti['user_id']

            group = Group.objects.get(course_id=course_id,
                                      group_id=group_id,
                                      role=role)
            if group.is_deleted:
                group.is_deleted = None
                group.deleted_by = None
                group.deleted_date = None
                group.provisioned_date = None
                group.added_date = datetime.datetime.utcnow().replace(tzinfo=utc)
            else:
                return self.json_response('{"error":" %s has duplicate role in course"}' % (group_id), status=400)
        except Group.DoesNotExist:
            try:
                self._group_policy.valid(group_id)
                group = Group(course_id=course_id,
                              group_id=group_id,
                              role=role)
            except GroupPolicyException as ex:
                self._log.error('POST: policy error: %s' % (ex))
                return self.json_response('{"error":"%s"}' % (ex), status=403)
        except Exception as ex:
            self._log.error('POST: error: %s' % (ex))
            return self.json_response('{"error": "%s"}' % (ex), status=400)

        group.priority=PRIORITY_IMMEDIATE
        group.added_by = user_id
        group.save()

        return self.json_response(json.dumps(group.json_data()))

    def DELETE(self, request, **kwargs):
        try:
            self._blti = BLTI().get_session(request)
        except BLTIException:
            return self.json_response(content="Unauthorized", status=401)

        try:
            id = self._valid_id(kwargs['id'])
            group = Group.objects.get(id=id)
            group.is_deleted = True
            group.deleted_date = datetime.datetime.utcnow().replace(tzinfo=utc)
            group.priority = PRIORITY_IMMEDIATE
            group.deleted_by = self._blti['user_id']
            group.save()

            ## only group use? mark member groups deleted too
            reused = Group.objects.filter(
                group_id=group.group_id,is_deleted__isnull=True).count()
            if reused == 0:
                for gmg in GroupMemberGroup.objects.filter(root_group_id=group.group_id,
                                                           is_deleted__isnull=True):
                    gmg.is_deleted = True
                    gmg.save()

        except Exception, err:
            self._log.error('DELETE: %s' % (err))
            return self.json_response('{"error":"%s"}' % (err), status=400)
        except Course.DoesNotExist:
            self._log.error('DELETE: group id not found: %s' % (id))
            return self.json_response('{"error":"Group not found: %s"}' % (id), status=404)

        return HttpResponse('')

    def _getGroupById(self, id):
        try:
            group = Group.objects.get(id=id).exclude(is_deleted=True)
            return self.json_response(json.dumps(group.json_data()))
        except Exception:
            self._log.error('group id not found: %s' % (id))
            return self.json_response('{"error":"Group id %s not found"}' % (id), status=404)

    def _getGroupsByQuery(self, request):
        json_rep = {
            'groups': []
        }

        terms = [
            ['queue_id', lambda x: x],
            ['course_id', lambda x: self._valid_course_id(x)],
            ['group_id', lambda x: self._valid_group_id(x)],
            ['role', lambda x: self._valid_role(x)]
        ]

        filter = {}

        try:
            for t in terms:
                value = request.GET.get(t[0])
                if value:
                    filter[t[0]] = t[1](value)

        except Exception, err:
            self._log.error('group query failure: %s' % (err))
            return self.json_response('{"error":"group query failure: %s"}' % (err), status=400)

        if len(filter) > 0:
            try:
                group_list = list(Group.objects.filter(**filter).exclude(is_deleted=True))
                for group in group_list:
                    json_rep['groups'].append(group.json_data())
            except Exception, err:
                self._log.error('group by queue_id fail: %s' % (err))
                return self.json_response('{"error":"%s"}' % (err), status=400)

        return self.json_response(json.dumps(json_rep))

    def _validate_post(self, values):
        return (
            self._valid_course_id(values.get('course_id')),
            self._valid_id(values.get('canvas_id')),
            self._valid_group_id(values.get('group_id').strip()),
            self._valid_role(values.get('role'))
        )

    def _valid_course_id(self, sis_id):
        self._course_policy.valid_sis_id(sis_id)
        try:
            course = Course.objects.get(course_id=sis_id)
        except Course.DoesNotExist:
            course = Course(course_id=sis_id,
                            course_type=Course.ADHOC_TYPE,
                            term_id='',
                            added_date=datetime.datetime.utcnow().replace(tzinfo=utc),
                            priority=PRIORITY_NONE)
            course.save()

        return course.course_id

    def _valid_group_id(self, id):
        self._group_policy.valid(id)
        return id.lower()

    def _valid_role(self, role):
        for r in self._blti.get("course_roles", []):
            if role == r:
                return role

        raise ValidationError("Invalid Role: %s" % (role))

    def _valid_id(self, id):
        if self._re_id.match(id):
            return id

        raise ValidationError('Invalid id: %s' % (id));


class GroupListView(RESTDispatch):
    """ Performs query of Group models at /api/v1/groups/?.
        GET returns 200 with Group models
    """
    def __init__(self):
        self._log = getLogger(__name__)

    def GET(self, request, **kwargs):
        json_rep = {
            'groups': []
        }

        group_list = list(Group.objects.all())
        for group in group_list:
            json_rep['groups'].append(group.json_data())

        return self.json_response(json.dumps(json_rep))

