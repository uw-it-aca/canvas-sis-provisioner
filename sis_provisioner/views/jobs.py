# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import json
from datetime import datetime, timezone
from logging import getLogger

from sis_provisioner.models import Job
from sis_provisioner.views.admin import RESTDispatch, get_user

logger = getLogger(__name__)


class JobView(RESTDispatch):
    """ Retrieves a Job model.
        GET returns 200 with Job details.
        PUT returns 200.
    """
    def get(self, request, *args, **kwargs):
        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            return self.json_response(job.json_data())
        except Job.DoesNotExist:
            return self.error_response(404, f"Job {job_id} not found")

    def put(self, request, *args, **kwargs):
        if not self.can_manage_jobs(request):
            return self.error_response(401, "Unauthorized")

        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)

            data = json.loads(request.body).get('job', {})
            if 'is_active' in data:
                job.is_active = data['is_active']
                job.changed_by = get_user(request)
                job.changed_date = datetime.now(timezone.utc)
                job.save()

                status = 'enabled' if job.is_active else 'disabled'
                logger.info(f'{job.changed_by} {status} Job "{job.name}"')

            return self.json_response({'job': job.json_data()})
        except Job.DoesNotExist:
            return self.error_response(404, f"Job {job_id} not found")

    def delete(self, request, *args, **kwargs):
        if not self.can_manage_jobs(request):
            return self.error_response(401, "Unauthorized")

        job_id = kwargs['job_id']
        try:
            job = Job.objects.get(id=job_id)
            job.delete()

            logger.info(f'{job.changed_by} deleted Job "{job.name}"')

            return self.json_response({'job': job.json_data()})
        except Job.DoesNotExist:
            return self.error_response(404, f"Job {job_id} not found")


class JobListView(RESTDispatch):
    """ Retrieves a list of Jobs.
    """
    def get(self, request, *args, **kwargs):
        read_only = not self.can_manage_jobs(request)
        jobs = []
        for job in Job.objects.all().order_by('title'):
            data = job.json_data()
            data['read_only'] = read_only
            jobs.append(data)

        return self.json_response({'jobs': jobs})
