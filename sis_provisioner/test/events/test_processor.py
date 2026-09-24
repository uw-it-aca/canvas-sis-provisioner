# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase, override_settings

from sis_provisioner.events import fix_key_url


class SISProvisionerProcessorTest(TestCase):
    @override_settings(RESTCLIENTS_KWS_HOST='https://ws.api.uw.edu:443')
    def test_fix_key_url(self):
        url = 'https://ws.admin.washington.edu:443/key/v1/encryption/889b7c21-d87.json'
        self.assertEqual(
            fix_key_url(url),
            'https://ws.api.uw.edu:443/key/v1/encryption/889b7c21-d87.json')

        url = 'https://ws.admin.washington.edu/key/v1/encryption/889b7c21-d87.json'
        self.assertEqual(
            fix_key_url(url),
            'https://ws.api.uw.edu:443/key/v1/encryption/889b7c21-d87.json')
