from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.term import get_current_active_term, get_term_after
from datetime import datetime


class TermListView(RESTDispatch):
    """ Retrieves a list of Terms.
    """
    def get(self, request, *args, **kwargs):
        curr_term = get_current_active_term(datetime.now())
        terms = {
            'current': curr_term.json_data(),
            'next': get_term_after(curr_term).json_data(),
        }
        return self.json_response({'terms': terms})
