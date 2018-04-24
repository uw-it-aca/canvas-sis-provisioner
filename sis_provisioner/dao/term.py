from django.conf import settings
from uw_sws.term import (
    get_term_by_year_and_quarter, get_term_after, get_term_before,
    get_term_by_date)
from uw_canvas.models import CanvasEnrollment
from restclients_core.exceptions import DataFailureException
from datetime import datetime, timedelta


TERM_DATE_FORMAT = '%Y-%m-%dT00:00:00-0800'


def get_current_active_term(dt):
    curr_term = get_term_by_date(dt.date())
    if dt > curr_term.grade_submission_deadline:
        curr_term = get_term_after(curr_term)
    return curr_term


def get_all_active_terms(dt):
    curr_term = get_current_active_term(dt)
    next_term = get_term_after(curr_term)
    return [curr_term, next_term, get_term_after(next_term)]


def is_active_term(term, dt=None):
    if dt is None:
        dt = datetime.now()
    return (term in get_all_active_terms(dt))


def term_sis_id(section):
    if section.is_independent_start:
        return getattr(settings, 'UWEO_INDIVIDUAL_START_TERM_SIS_ID',
                       'uweo-individual-start')
    else:
        return section.term.canvas_sis_id()


def term_name(section):
    if section.is_independent_start:
        return getattr(settings, 'UWEO_INDIVIDUAL_START_TERM_NAME',
                       'UWEO Individual Start')
    else:
        return '%s %s' % (section.term.quarter.capitalize(), section.term.year)


def term_start_date(section):
    if section.is_independent_start:
        return None
    else:
        return quarter_term_start_date(section.term).strftime(TERM_DATE_FORMAT)


def term_end_date(section):
    if section.is_independent_start:
        return None
    else:
        return quarter_term_end_date(section.term).strftime(TERM_DATE_FORMAT)


def term_date_overrides(term):
    overrides = {}
    for role_choice in CanvasEnrollment.ROLE_CHOICES:
        role = role_choice[0]
        if role == CanvasEnrollment.OBSERVER:
            continue
        elif role == CanvasEnrollment.TEACHER:
            overrides[role] = (
                (quarter_term_start_date(term) - timedelta(days=365)).strftime(
                    TERM_DATE_FORMAT),
                (quarter_term_end_date(term) + timedelta(days=365*2)).strftime(
                    TERM_DATE_FORMAT))
        else:
            overrides[role] = (
                (quarter_term_start_date(term) - timedelta(days=365)).strftime(
                    TERM_DATE_FORMAT),
                (quarter_term_end_date(term) + timedelta(days=365)).strftime(
                    TERM_DATE_FORMAT))

    return overrides


def quarter_term_start_date(term):
    return term.first_day_quarter


def quarter_term_end_date(term):
    return (term.grade_submission_deadline + timedelta(days=1)).date()
