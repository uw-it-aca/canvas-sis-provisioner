# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.apps import AppConfig


class SISProvisionerConfig(AppConfig):
    name = 'sis_provisioner'

    def ready(self):
        import sis_provisioner.signals
