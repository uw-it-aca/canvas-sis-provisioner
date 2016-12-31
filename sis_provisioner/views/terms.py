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
            'current': curr_term.json_data(),
            'next': get_term_after(curr_term).json_data(),
        }
        return self.json_response(json.dumps({'terms': terms}))
