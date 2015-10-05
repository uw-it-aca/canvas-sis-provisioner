from sis_provisioner.policy import UserPolicy


def regid_from_request(data):
    regid = data.get('reg_id', '').strip().upper()
    UserPolicy().valid_reg_id(regid)
    return regid


def netid_from_request(data):
    netid = data.get('net_id', '').strip().lower()
    UserPolicy().valid_net_id(netid)
    return netid
