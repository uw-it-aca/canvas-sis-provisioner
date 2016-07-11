from django.apps import AppConfig


class SISProvisionerConfig(AppConfig):
    name = 'sis_provisioner'

    def ready(self):
        import sis_provisioner.signals
