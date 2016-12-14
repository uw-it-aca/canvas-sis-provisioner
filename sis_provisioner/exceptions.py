"""
Contains the custom exceptions used by sis_provisioner.
"""


class UserPolicyException(Exception):
    pass


class MissingLoginIdException(UserPolicyException):
    pass


class TemporaryNetidException(UserPolicyException):
    pass


class InvalidLoginIdException(UserPolicyException):
    pass


class GroupPolicyException(Exception):
    pass


class GroupNotFoundException(GroupPolicyException):
    pass


class GroupUnauthorizedException(GroupPolicyException):
    pass


class CoursePolicyException(Exception):
    pass


class EnrollmentPolicyException(Exception):
    pass


class AccountPolicyException(Exception):
    pass


class EmptyQueueException(Exception):
    pass


class MissingImportPathException(Exception):
    pass
