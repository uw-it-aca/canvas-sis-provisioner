from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.models.events import (
    EnrollmentLog, GroupLog, InstructorLog, PersonLog)
from time import time, gmtime, strftime
from calendar import timegm
from math import floor
import dateutil.parser


class EventListView(RESTDispatch):
    """
    Expose ranges of event counts
    """
    def get(self, request, *args, **kwargs):
        try:
            event_types = request.GET.get('type', 'enrollment')
            start_sample = int(floor(time() / 60))  # default to now
            end_sample = start_sample

            utc_str = request.GET.get('on')
            if utc_str is not None:
                start_sample = self._start_minutes(utc_str)
                end_sample = start_sample
            else:
                utc_str = request.GET.get('begin')
                if utc_str is not None:
                    start_sample = self._start_minutes(utc_str)
                    utc_str = request.GET.get('end')
                    if utc_str is not None:
                        end_sample = self._start_minutes(utc_str)
                        if (start_sample > end_sample):
                            t = start_sample
                            start_sample = end_sample
                            end_sample = t

            events = {}
            for event_type in event_types.split(','):
                events[event_type] = {
                    'start': strftime("%Y-%m-%dT%H:%M:%SZ",
                                      gmtime(start_sample * 60)),
                    'end': strftime("%Y-%m-%dT%H:%M:%SZ",
                                    gmtime(end_sample * 60)),
                    'points': [0 for i in xrange(
                        (end_sample - start_sample + 1))]
                }

                if event_type == 'enrollment':
                    event_log = EnrollmentLog.objects.filter(
                        minute__gte=start_sample)
                elif event_type == 'instructor':
                    event_log = InstructorLog.objects.filter(
                        minute__gte=start_sample)
                elif event_type == 'group':
                    event_log = GroupLog.objects.filter(
                        minute__gte=start_sample)
                elif event_type == 'person':
                    event_log = PersonLog.objects.filter(
                        minute__gte=start_sample)
                else:
                    raise Exception('unknown event type %s' % event_type)

                for o in event_log:
                    try:
                        events[event_type]['points'][
                            o.minute - start_sample] = o.event_count
                    except Exception:
                        pass

            return self.json_response(events)
        except Exception as err:
            return self.error_response(400, "Invalid event search: %s" % err)

    def _start_minutes(self, utc_str):
        utc = dateutil.parser.parse(utc_str)
        return int(floor(timegm(utc.timetuple()) / 60))
