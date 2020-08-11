from .base_settings import *
import os

INSTALLED_APPS += [
    'compressor',
    'django.contrib.humanize',
    'django_user_agents',
    'supporttools',
    'rc_django',
    'blti',
    'groups',
    'libguide',
    'course_roster',
    'canvas_users',
    'grading_standard',
    'anonymous_feedback',
    'grade_conversion_calculator',
    'sis_provisioner.apps.SISProvisionerConfig',
]

# Assign rather than append since order of BLTI middleware is significant
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.common.CommonMiddleware',
    'blti.middleware.CSRFHeaderMiddleware',
    'blti.middleware.SessionHeaderMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

TEMPLATES[0]['OPTIONS']['context_processors'].extend([
    'supporttools.context_processors.supportools_globals'
])

COMPRESS_ROOT = '/static/'

STATICFILES_FINDERS += (
    'compressor.finders.CompressorFinder',
)

COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
    ('text/x-sass', 'pyscss {infile} > {outfile}'),
    ('text/x-scss', 'pyscss {infile} > {outfile}'),
)

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
]

COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter',
]

COMPRESS_OFFLINE = True

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_DOMAIN = '.uw.edu'

if os.getenv('ENV', 'localdev') == 'localdev':
    DEBUG = True
    SIS_IMPORT_CSV_DEBUG = True
    CANVAS_MANAGER_ADMIN_GROUP = 'u_test_group'
    RESTCLIENTS_ADMIN_GROUP = 'u_test_group'
    RESTCLIENTS_DAO_CACHE_CLASS = None
    CANVAS_ACCOUNT_ID = '12345'
else:
    SIS_IMPORT_CSV_DEBUG = False
    CANVAS_MANAGER_ADMIN_GROUP = os.getenv('ADMIN_GROUP', '')
    RESTCLIENTS_ADMIN_GROUP = os.getenv('SUPPORT_GROUP', '')
    RESTCLIENTS_DAO_CACHE_CLASS = 'sis_provisioner.cache.RestClientsCache'

RESTCLIENTS_DISABLE_THREADING = True
RESTCLIENTS_ADMIN_AUTH_MODULE = 'sis_provisioner.views.admin.can_view_source_data'
SUPPORTTOOLS_PARENT_APP = 'Canvas LMS'

try:
    SUPPORTTOOLS_PARENT_APP_URL = RESTCLIENTS_CANVAS_HOST
except NameError:
    SUPPORTTOOLS_PARENT_APP_URL = '/'

EVENT_AWS_SQS_CERT = os.getenv('AWS_SQS_CERT', '')
EVENT_AWS_SQS_KEY = os.getenv('AWS_SQS_KEY', '')

AWS_CA_BUNDLE = RESTCLIENTS_CA_BUNDLE
AWS_SQS = {
    'ENROLLMENT_V2': {
        'QUEUE_ARN': os.getenv('SQS_ENROLLMENT_QUEUE_ARN', ''),
        'KEY_ID': os.getenv('SQS_ENROLLMENT_KEY_ID', ''),
        'KEY': os.getenv('SQS_ENROLLMENT_KEY', ''),
        'VISIBILITY_TIMEOUT': 60,
        'MESSAGE_GATHER_SIZE': 10,
        'VALIDATE_SNS_SIGNATURE': True,
        'EVENT_COUNT_PRUNE_AFTER_DAY': 2,
        'VALIDATE_BODY_SIGNATURE': True,
    },
    'INSTRUCTOR_ADD': {
        'QUEUE_ARN': os.getenv('SQS_INSTRUCTOR_ADD_QUEUE_ARN', ''),
        'KEY_ID': os.getenv('SQS_INSTRUCTOR_ADD_KEY_ID', ''),
        'KEY': os.getenv('SQS_INSTRUCTOR_ADD_KEY', ''),
        'VISIBILITY_TIMEOUT': 60,
        'MESSAGE_GATHER_SIZE': 10,
        'VALIDATE_SNS_SIGNATURE': True,
        'EVENT_COUNT_PRUNE_AFTER_DAY': 2,
        'VALIDATE_BODY_SIGNATURE': False,
    },
    'INSTRUCTOR_DROP': {
        'QUEUE_ARN': os.getenv('SQS_INSTRUCTOR_DROP_QUEUE_ARN', ''),
        'KEY_ID': os.getenv('SQS_INSTRUCTOR_DROP_KEY_ID', ''),
        'KEY': os.getenv('SQS_INSTRUCTOR_DROP_KEY', ''),
        'VISIBILITY_TIMEOUT': 60,
        'MESSAGE_GATHER_SIZE': 10,
        'VALIDATE_SNS_SIGNATURE': True,
        'EVENT_COUNT_PRUNE_AFTER_DAY': 2,
        'VALIDATE_BODY_SIGNATURE': False,
    },
    'GROUP': {
        'QUEUE_ARN': os.getenv('SQS_GROUP_QUEUE_ARN', ''),
        'KEY_ID': os.getenv('SQS_GROUP_KEY_ID', ''),
        'KEY': os.getenv('SQS_GROUP_KEY', ''),
        'VISIBILITY_TIMEOUT': 60,
        'MESSAGE_GATHER_SIZE': 10,
        'VALIDATE_SNS_SIGNATURE': True,
        'EVENT_COUNT_PRUNE_AFTER_DAY': 2,
        'VALIDATE_BODY_SIGNATURE': True,
        'BODY_DECRYPT_KEYS': {
            'iamcrypt1': os.getenv('SQS_GROUP_DECRYPT_KEY', ''),
        },
    },
    'PERSON_V1': {
        'QUEUE_ARN': os.getenv('SQS_PERSON_QUEUE_ARN', ''),
        'KEY_ID': os.getenv('SQS_PERSON_KEY_ID', ''),
        'KEY': os.getenv('SQS_PERSON_KEY', ''),
        'VISIBILITY_TIMEOUT': 60,
        'MESSAGE_GATHER_SIZE': 10,
        'VALIDATE_SNS_SIGNATURE': True,
        'EVENT_COUNT_PRUNE_AFTER_DAY': 2,
        'VALIDATE_BODY_SIGNATURE': False,
    },
}

ASTRA_ROLE_MAPPING = {
    "accountadmin": "AccountAdmin",
    "tier1support": "UW-IT Support Tier 1",
    "tier2support": "UW-IT Support Tier 2",
    "CollDeptAdminCourseDesign": "College or Dept Admin or Designer",
    "CollDeptSuptOutcomeMgr": "College or Dept Support or Outcomes Manager",
    "CollDeptResearchObserve": "College or Dept Researcher or Observer",
    "DisabilityResourcesAdm": "Disability Resources Admin",
    "UWEOAdmin": "UWEO Admin",
    "UWEOManager": "UWEO Manager",
    "UWEOProgram": "UWEO Program",
    "UWEOOperations": "UWEO Operations",
    "UWEOReadOnly": "UWEO Read Only",
    "APIUserReadOnly": "API User (Read Only)",
    "APIUserReadWrite": "API User (Read-Write)",
    "AllyApplication": "Ally application"
}

CANVAS_MASQUERADE_ROLE = "Become users only (dept. admin)"
ANCILLARY_CANVAS_ROLES = {
    "CollDeptAdminCourseDesign": {
        "account": "root",
        "canvas_role": CANVAS_MASQUERADE_ROLE
    },
    "UWEOAdmin": {
        "account": "root",
        "canvas_role": CANVAS_MASQUERADE_ROLE
    },
    "UWEOManager": {
        "account": "root",
        "canvas_role": CANVAS_MASQUERADE_ROLE
    },
}

LTI_ENFORCE_SSL = False
LTI_CONSUMERS = {}

BLTI_AES_KEY = bytes(os.getenv('BLTI_AES_KEY', ''))
BLTI_AES_IV = bytes(os.getenv('BLTI_AES_IV', ''))

UW_GROUP_BLACKLIST = [
    'uw_affiliation_',
    'uw_employee',
    'uw_faculty',
    'uw_staff',
    'uw_student',
    'uw_affiliate',
    'uw_member'
]

DEFAULT_GROUP_SECTION_NAME = 'UW Group members'

LOGIN_DOMAIN_WHITELIST = ['gmail.com', 'google.com', 'googlemail.com']
ADD_USER_DOMAIN_WHITELIST = [
    'uw.edu', 'washington.edu', 'u.washington.edu', 'cac.washington.edu']

PERMISSIONS_CHECK_ACCOUNTS = [CANVAS_ACCOUNT_ID, '103216']

SIS_IMPORT_ROOT_ACCOUNT_ID = 'uwcourse'
SIS_IMPORT_CSV_ROOT = os.getenv('SIS_IMPORT_CSV_ROOT', '')
SIS_IMPORT_GROUPS = ['uw_student', 'uw_faculty', 'uw_staff']
SIS_IMPORT_IMMEDIATE_COURSE_SOCKET = os.getenv('SIS_IMPORT_IMMEDIATE_COURSE_SOCKET', '')
SIS_IMPORT_LIMIT = {
    'course': {
        'default': 500,
        'high': 200
    },
    'enrollment': {
        'default': 1000,
        'high': 100
    },
    'user': {
        'default': 500,
        'high': 500
    },
    'group': {
        'default': 0,
        'high': 20
    },
}

NONPERSONAL_NETID_EXCEPTION_GROUP = 'u_acadev_canvas_nonpersonal_netids'

LMS_OWNERSHIP_SUBACCOUNT = {
    'PCE_AP': 'uwcourse:uweo:ap-managed',
    'PCE_IELP': 'uwcourse:uweo:ielp-managed',
    'PCE_OL': 'uwcourse:uweo:ol-managed',
    'PCE_NONE': 'uwcourse:uweo:noncredit-campus-managed'
}

ADMIN_EVENT_GRAPH_FREQ = 10
ADMIN_IMPORT_STATUS_FREQ = 30
