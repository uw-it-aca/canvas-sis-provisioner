# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.views.admin import RESTDispatch
from sis_provisioner.dao.term import get_current_active_term, get_term_after


class TermListView(RESTDispatch):
    """ Retrieves a list of Terms.
    """
    def get(self, request, *args, **kwargs):
        curr_term = get_current_active_term()
        terms = {
            'current': curr_term.json_data(),
            'next': get_term_after(curr_term).json_data(),
        }
        return self.json_response({'terms': terms})
