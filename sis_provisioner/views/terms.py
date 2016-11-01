from sis_provisioner.views.rest_dispatch import RESTDispatch
from sis_provisioner.dao.term import get_term_by_date, get_term_after
from datetime import datetime
import json


class TermListView(RESTDispatch):
    """ Retrieves a list of Terms.
    """
    def GET(self, request, **kwargs):
        curr_term = get_term_by_date(datetime.now().date())
        terms = {
            'current': self._load_term(curr_term),
            'next': self._load_term(get_term_after(curr_term))
        }

        return self.json_response(json.dumps({'terms': terms}))

    def _load_term(self, term):
        data = term.json_data()
        data['label'] = term.term_label()
        data['first_day_quarter'] = term.first_day_quarter.strftime(
            "%Y-%m-%d %H:%M")
        data['last_day_instruction'] = term.last_day_instruction.strftime(
            "%Y-%m-%d %H:%M")
        data['last_final_exam_date'] = term.last_final_exam_date.strftime(
            "%Y-%m-%d %H:%M")
        data['enrollment_data'] = [
            [term.registration_period1_start.strftime("%Y-%m-%d 06:00"),
             term.registration_period1_end.strftime("%Y-%m-%d 23:59")],
            [term.registration_period2_start.strftime("%Y-%m-%d 06:00"),
             term.registration_period2_end.strftime("%Y-%m-%d 23:59")],
            [term.registration_period3_start.strftime("%Y-%m-%d 06:00"),
             term.registration_period3_end.strftime("%Y-%m-%d 23:59")]]
        return data
