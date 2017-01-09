from restclients.sws.registration import get_all_registrations_by_section
from sis_provisioner.models import Enrollment
from sis_provisioner.dao import localize


def enrollment_status_from_registration(registration):
    request_status = registration.request_status.lower()
    if (registration.is_active or request_status == 'added to standby' or
            request_status == 'pending added to class'):
        return Enrollment.ACTIVE_STATUS

    if (localize(registration.request_date) >
            localize(registration.section.term.get_eod_census_day())):
        return Enrollment.INACTIVE_STATUS
    else:
        return Enrollment.DELETED_STATUS


def get_registrations_by_section(section):
    registrations = get_all_registrations_by_section(
        section, transcriptable_course='all')

    # Sort by regid-duplicate code, and keep the last one
    registrations.sort(key=lambda r: (r.person.uwregid, r.duplicate_code))

    uniques = {}
    for registration in registrations:
        uniques[registration.person.uwregid] = registration

    return sorted(uniques.values(), key=lambda r: r.person.uwregid)
