from sis_provisioner.dao.user import valid_net_id, valid_reg_id


def regid_from_request(data):
    regid = data.get('reg_id', '').strip().upper()
    valid_reg_id(regid)
    return regid


def netid_from_request(data):
    netid = data.get('net_id', '').strip().lower()
    valid_net_id(netid)
    return netid
