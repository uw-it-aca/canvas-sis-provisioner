from .base_settings import *
from google.oauth2 import service_account
import os

INSTALLED_APPS += [
    'compressor',
    'django.contrib.humanize',
    'django_user_agents',
    'supporttools',
    'rc_django',
    'analytics',
    'rest_framework.authtoken',
    'sis_provisioner.apps.SISProvisionerConfig',
]

MIDDLEWARE += [
    'userservice.user.UserServiceMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
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
    RESTCLIENTS_CANVAS_ACCOUNT_ID = '12345'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = os.getenv('SIS_IMPORT_CSV_ROOT', '/app/csv')
else:
    SIS_IMPORT_CSV_DEBUG = False
    CANVAS_MANAGER_ADMIN_GROUP = os.getenv('ADMIN_GROUP', '')
    RESTCLIENTS_ADMIN_GROUP = os.getenv('SUPPORT_GROUP', '')
    RESTCLIENTS_DAO_CACHE_CLASS = 'sis_provisioner.cache.RestClientsCache'
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_PROJECT_ID = os.getenv('STORAGE_PROJECT_ID', '')
    GS_BUCKET_NAME = os.getenv('STORAGE_BUCKET_NAME', '')
    GS_LOCATION = os.path.join(os.getenv('SIS_IMPORT_CSV_ROOT', ''))
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        '/gcs/credentials.json')

    DATABASES['analytics'] = {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.getenv('ANALYTICS_DATABASE_HOSTNAME', 'localhost'),
        'NAME': os.getenv('ANALYTICS_DATABASE_NAME', 'canvas_analytics'),
        'USER': os.getenv('ANALYTICS_DATABASE_USERNAME', None),
        'PASSWORD': os.getenv('ANALYTICS_DATABASE_PASSWORD', None),
    }

    DATABASE_ROUTERS = ['sis_provisioner.models.router.AnalyticsRouter']

RESTCLIENTS_DISABLE_THREADING = True
RESTCLIENTS_ADMIN_AUTH_MODULE = 'sis_provisioner.views.admin.can_view_source_data'
SUPPORTTOOLS_PARENT_APP = 'Canvas LMS'

try:
    SUPPORTTOOLS_PARENT_APP_URL = RESTCLIENTS_CANVAS_HOST
except NameError:
    SUPPORTTOOLS_PARENT_APP_URL = '/'

EVENT_AWS_SQS_CERT = os.getenv('AWS_SQS_CERT', APPLICATION_CERT_PATH)
EVENT_AWS_SQS_KEY = os.getenv('AWS_SQS_KEY', APPLICATION_KEY_PATH)

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
    "AllyApplication": "Ally application",
    "NoodleManager": "Noodle Manager",
    "NoodleTermPrep": "Noodle Term Prep",
    "NoodleInstDesigner": "Noodle Instructional Designer",
    "NoodleStdScsCoach": "Noodle Student Success Coach",
    "NoodleSupportDesk": "Noodle Support Desk",
    "NoodleAPISvcAccount": "Noodle API Service Account",
    "NoodleLCMSAPI": "Noodle LCMS API"
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
    "NoodleManager": {
        "account": "root",
        "canvas_role": CANVAS_MASQUERADE_ROLE
    },
    "NoodleSupportDesk": {
        "account": "root",
        "canvas_role": CANVAS_MASQUERADE_ROLE
    },
}

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

CONTINUUM_ACCOUNT_ID = os.getenv('CONTINUUM_ACCOUNT_ID', '')
PERMISSIONS_CHECK_ACCOUNTS = [RESTCLIENTS_CANVAS_ACCOUNT_ID, CONTINUUM_ACCOUNT_ID]

SIS_IMPORT_ROOT_ACCOUNT_ID = 'uwcourse'
SIS_IMPORT_GROUPS = ['uw_student', 'uw_faculty', 'uw_staff']
SIS_IMPORT_LIMIT = {
    'course': {
        'default': 400,
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
ASTRA_ADMIN_EXCEPTIONS = [
    'conditional-release-service@instructure.auth',
    'readygoadmin@cidilabs.com',
    'a_gradeit_canvas_int',
]

LMS_OWNERSHIP_SUBACCOUNT = {
    'PCE_AP': 'uwcourse:uweo:ap-managed',
    'PCE_IELP': 'uwcourse:uweo:ielp-managed',
    'PCE_OL': 'uwcourse:uweo:ol-managed',
    'PCE_NONE': 'uwcourse:uweo:noncredit-campus-managed',
    'ISCHOOL': 'canvas_104251',
}

ADMIN_EVENT_GRAPH_FREQ = 10
ADMIN_IMPORT_STATUS_FREQ = 30

REMOVED_ADMIN_RETENTION_DAYS = 90
ENROLLMENT_EVENT_RETENTION_DAYS = 180

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'stdout_stream': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.levelno < logging.WARNING
        },
        'stderr_stream': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.levelno > logging.ERROR
        }
    },
    'formatters': {
        'sis_provisioner': {
            'format': '%(levelname)-4s %(asctime)s %(module)s %(message)s [%(name)s]',
            'datefmt': '[%Y-%m-%d %H:%M:%S]',
        },
        'restclients_timing': {
            'format': '%(levelname)-4s restclients_timing %(module)s %(asctime)s %(message)s [%(name)s]',
            'datefmt': '[%Y-%m-%d %H:%M:%S]',
        },
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'filters': ['stdout_stream'],
            'formatter': 'sis_provisioner',
        },
        'stderr': {
            'class': 'logging.StreamHandler',
            'stream': sys.stderr,
            'filters': ['stderr_stream'],
            'formatter': 'sis_provisioner',
        },
        'restclients_timing': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'filters': ['stdout_stream'],
            'formatter': 'restclients_timing',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django.request': {
            'handlers': ['stderr'],
            'level': 'ERROR',
            'propagate': True,
        },
        'sis_provisioner': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': True,
        },
        'restclients_core': {
            'handlers': ['restclients_timing'],
            'level': 'INFO',
            'propagate': False,
        },
        'aws_message': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'groups': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
        },
        'blti': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['stdout', 'stderr'],
            'level': 'INFO' if os.getenv('ENV', 'localdev') == 'prod' else 'DEBUG'
        }
    }
}
