# Copyright 2024 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.http import HttpResponse
from django.core.exceptions import ValidationError
from sis_provisioner.models.group import Group, GroupMemberGroup
from sis_provisioner.models.course import Course
from sis_provisioner.dao.group import valid_group_id
from sis_provisioner.dao.course import (
    valid_canvas_course_id, valid_course_sis_id, adhoc_course_sis_id)
from sis_provisioner.exceptions import (
    GroupPolicyException, CoursePolicyException)
from blti.views import BLTILaunchView, RESTDispatch
from logging import getLogger
from datetime import datetime, timezone
import json
import re

logger = getLogger(__name__)


class GroupsLaunchView(BLTILaunchView):
    template_name = 'groups/main.html'
    authorized_role = 'admin'

    def get_context_data(self, **kwargs):
        if self.blti.course_sis_id is not None:
            course_sis_id = self.blti.course_sis_id
        else:
            course_sis_id = adhoc_course_sis_id(self.blti.canvas_course_id)

        return {
            'session_id': self.request.session.session_key,
            'sis_course_id': course_sis_id,
            'canvas_course_id': self.blti.canvas_course_id,
            'canvas_account_id': self.blti.canvas_account_id,
            'launch_presentation_return_url': self.blti.return_url,
        }


class GroupView(RESTDispatch):
    """ Exposes Group model
        GET returns Group details
        POST inserts new Group
        DELETE removes Group
    """
    authorized_role = 'admin'

    def get(self, request, *args, **kwargs):
        group_id = kwargs.get('id')
        if group_id is not None:
            return self._getGroupById(group_id)
        else:
            return self._getGroupsByQuery(request)

    def post(self, request, *args, **kwargs):
        try:
            course_id, canvas_id, group_id, role = self._validate_post(request)
            group = Group.objects.get(course_id=course_id,
                                      group_id=group_id,
                                      role=role)
            if group.is_deleted:
                group.is_deleted = None
                group.deleted_by = None
                group.deleted_date = None
                group.provisioned_date = None
                group.added_date = datetime.now(timezone.utc)
            else:
                return self.error_response(
                    400, 'Group {} has duplicate role in course'.format(
                        group_id))

        except Group.DoesNotExist:
            try:
                valid_group_id(group_id)
                group = Group(course_id=course_id,
                              group_id=group_id,
                              role=role)
            except GroupPolicyException as ex:
                logger.info('POST policy error: {}'.format(ex))
                return self.error_response(403, ex)
        except (CoursePolicyException, GroupPolicyException,
                ValidationError) as ex:
            logger.info('POST error: {}'.format(ex))
            return self.error_response(400, ex)

        group.priority = Course.PRIORITY_IMMEDIATE
        group.added_by = self.blti.user_login_id
        group.save()

        return self.json_response(group.json_data())

    def delete(self, request, *args, **kwargs):
        try:
            id = self._valid_model_id(kwargs['id'])
            group = Group.objects.get(id=id)
            group.is_deleted = True
            group.deleted_date = datetime.now(timezone.utc)
            group.priority = Course.PRIORITY_IMMEDIATE
            group.deleted_by = self.blti.user_login_id
            group.save()

            # only group use? mark member groups deleted too
            reused = Group.objects.filter(
                group_id=group.group_id, is_deleted__isnull=True).count()
            if reused == 0:
                for gmg in GroupMemberGroup.objects.filter(
                        root_group_id=group.group_id, is_deleted__isnull=True):
                    gmg.is_deleted = True
                    gmg.save()

        except ValidationError as err:
            logger.info('DELETE group error: {}'.format(err))
            return self.error_response(400, err)
        except Group.DoesNotExist:
            return self.error_response(404, 'Group not found ({})'.format(id))

        return HttpResponse('')

    def _getGroupById(self, id):
        try:
            group = Group.objects.get(id=id, is_deleted=None)
            return self.json_response(group.json_data())
        except Group.DoesNotExist:
            return self.error_response(404, 'Group id {} not found'.format(id))

    def _getGroupsByQuery(self, request):
        terms = {
            'queue_id': lambda x: self._valid_model_id(x),
            'course_id': lambda x: self._valid_course_id(x),
            'group_id': lambda x: self._valid_group_id(x),
            'role': lambda x: self._valid_role(x)}

        kwargs = {}
        for key in terms:
            try:
                kwargs[key] = terms[key](request.GET.get(key))
            except (CoursePolicyException, GroupPolicyException,
                    ValidationError):
                pass

        if not len(kwargs):
            return self.error_response(400, 'Invalid search: No search terms')

        groups = []
        for group in Group.objects.find_by_search(**kwargs):
            groups.append(group.json_data())

        return self.json_response({'groups': groups})

    def _validate_post(self, request):
        values = json.loads(request.read())
        return (
            self._valid_course_id(values.get('course_id')),
            self._valid_canvas_id(values.get('canvas_id')),
            self._valid_group_id(values.get('group_id').strip()),
            self._valid_role(values.get('role'))
        )

    def _valid_course_id(self, sis_id):
        valid_course_sis_id(sis_id)
        try:
            course = Course.objects.get(course_id=sis_id)
        except Course.DoesNotExist:
            course = Course(
                course_id=sis_id,
                course_type=Course.ADHOC_TYPE,
                term_id='',
                added_date=datetime.now(timezone.utc)
                priority=Course.PRIORITY_NONE)
            course.save()

        return course.course_id

    def _valid_group_id(self, group_id):
        valid_group_id(group_id)
        return group_id.lower()

    def _valid_role(self, role):
        if role is not None and len(role):
            return role
        raise ValidationError("Invalid Role: {}".format(role))

    def _valid_canvas_id(self, course_id):
        valid_canvas_course_id(course_id)
        return course_id

    def _valid_model_id(self, model_id):
        re_model_id = re.compile(r"^\d+$")
        if (re_model_id.match(str(model_id)) is None):
            raise ValidationError("Invalid ID: {}".format(model_id))
        return model_id
