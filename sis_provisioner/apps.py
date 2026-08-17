# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import os

from django.apps import AppConfig
from restclients_core.dao import MockDAO


class SISProvisionerConfig(AppConfig):
    name = 'sis_provisioner'

    def ready(self):
        import sis_provisioner.signals  # noqa: F401

        mocks = os.path.join(os.path.dirname(__file__), 'resources')
        MockDAO.register_mock_path(mocks)
