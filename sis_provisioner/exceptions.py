# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from restclients_core.exceptions import DataFailureException


class UserPolicyException(Exception):
    pass


class MissingLoginIdException(UserPolicyException):
    pass


class MissingStudentNumberException(UserPolicyException):
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
