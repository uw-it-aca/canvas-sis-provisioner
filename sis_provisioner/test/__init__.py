from django.conf import settings
from sis_provisioner.models import Admin
import binascii
import os


def create_admin(net_id, account_id='test', role='accountadmin',
                 reg_id=binascii.b2a_hex(os.urandom(16)).upper(),
                 canvas_id=None):
    if canvas_id is None:
        canvas_id = settings.RESTCLIENTS_CANVAS_ACCOUNT_ID

    admin = Admin(net_id=net_id, reg_id=reg_id, account_id=account_id,
                  canvas_id=canvas_id, role=role)
    admin.save()
    return admin
