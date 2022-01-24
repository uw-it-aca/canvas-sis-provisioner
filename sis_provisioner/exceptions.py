# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

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


class EventException(Exception):
    pass


class UnhandledActionCodeException(Exception):
    pass


class ASTRAException(Exception):
    pass
