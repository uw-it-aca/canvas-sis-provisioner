from django.conf import settings
from restclients.pws import PWS
from restclients.gws import GWS
from restclients.exceptions import InvalidGroupID, DataFailureException
from restclients.models.canvas import CanvasUser
from restclients.models.sws import Section
from sis_provisioner.models import Curriculum, SubAccountOverride, TermOverride
from datetime import timedelta
import re


class UserPolicyException(Exception):
    pass


class GroupPolicyException(Exception):
    pass


class GroupNotFoundException(Exception):
    pass


class GroupUnauthorizedException(Exception):
    pass


class CoursePolicyException(Exception):
    pass


class UserPolicy(object):
    def __init__(self):
        """
        Enforce Acceptable User policy: netids and acceptable domains
        """
        # Admin NetIDs
        self._admin_net_id_whitelist = self._whitelist_regex(
            ['[a-z]adm_[a-z][a-z0-9]{0,7}'])

        # Application NetIDs
        self._application_net_id_whitelist = self._whitelist_regex(
            ['a_[\w]{1,18}'])

        # Temporary NetIDs
        self._temp_net_id_whitelist = self._whitelist_regex(
            ['(?:css|wire|lib|event)[0-9]{4,}'])
        self._re_canvas_id = re.compile(r"^\d+$")
        self._pws = PWS()
        self._gws = GWS()

    def valid(self, login_id):
        try:
            self.valid_net_id(login_id)
        except UserPolicyException:
            try:
                self.valid_reg_id(login_id)
            except UserPolicyException:
                self.valid_gmail_id(login_id)

    def valid_net_id(self, login_id):
        if not login_id:
            raise UserPolicyException('Missing UWNetID')

        if self._temp_net_id_whitelist.match(login_id):
            raise UserPolicyException('Temporary UWNetID not permitted')

        if not self._pws.valid_uwnetid(login_id):
            raise UserPolicyException('Not a valid UWNetID')

    def valid_admin_net_id(self, login_id):
        if self._admin_net_id_whitelist.match(login_id) is None:
            raise UserPolicyException('Not a valid Admin UWNetID')

    def valid_application_net_id(self, login_id):
        if self._application_net_id_whitelist.match(login_id) is None:
            raise UserPolicyException('Not a valid Application UWNetID')

    def valid_nonpersonal_net_id(self, netid):
        try:
            self.valid_admin_net_id(netid)
        except UserPolicyException:
            try:
                self.valid_application_net_id(netid)
            except UserPolicyException:
                group = getattr(settings, 'NONPERSONAL_NETID_EXCEPTION_GROUP',
                                '')
                try:
                    if not self._gws.is_effective_member(group, netid):
                        raise UserPolicyException('UWNetID not permitted')
                except InvalidGroupID as err:
                    raise UserPolicyException('UWNetID not permitted')

    def valid_reg_id(self, regid):
        if not self._pws.valid_uwregid(regid):
            raise UserPolicyException('Not a valid UWRegID')

    def valid_gmail_id(self, login_id):
        try:
            (username, domain) = login_id.lower().split("@")
            username = username.split("+", 1)[0].replace(".", "")
            if not len(username):
                raise UserPolicyException(
                    "Invalid username: %s" % login_id)
        except:
            raise UserPolicyException("Invalid username: %s" % login_id)

        if domain not in getattr(settings, 'LOGIN_DOMAIN_WHITELIST', []):
            raise UserPolicyException("Invalid domain: %s" % login_id)

        return "%s@%s" % (username, domain)

    def valid_canvas_id(self, canvas_id):
        if (self._re_canvas_id.match(canvas_id) is None):
            raise UserPolicyException("Invalid Canvas ID: %s" % canvas_id)

    def get_person_by_netid(self, netid):
        try:
            self.valid_net_id(netid)
            person = self._pws.get_person_by_netid(netid)

        except DataFailureException, err:
            if err.status == 404:  # Non-personal netid?
                self.valid_nonpersonal_net_id(netid)
                person = self._pws.get_entity_by_netid(netid)
            else:
                raise

        return person

    def get_person_by_regid(self, regid):
        try:
            person = self._pws.get_person_by_regid(regid)
            self.valid_net_id(person.uwnetid)

        except DataFailureException, err:
            if err.status == 404:  # Non-personal regid?
                person = self._pws.get_entity_by_regid(regid)
                self.valid_nonpersonal_net_id(person.netid)
            else:
                raise

        return person

    def get_person_by_gmail_id(self, gmail_id):
        sis_user_id = self.valid_gmail_id(gmail_id)
        return CanvasUser(sis_user_id=sis_user_id,
                          login_id=gmail_id.lower(),
                          email=gmail_id)

    def _whitelist_regex(self, whitelist):
        return re.compile(r'^(%s)$' % ('|'.join(whitelist)), re.I)


class GroupPolicy(object):
    def __init__(self):
        policy = r'^(%s).*$' % ('|'.join(
            getattr(settings, 'UW_GROUP_BLACKLIST', [])))
        self._policy_restricted = re.compile(policy, re.I)
        self._gws = GWS()

    def valid(self, group_id):
        if not self._gws._is_valid_group_id(group_id):
            raise GroupPolicyException("Invalid Group ID: %s" % group_id)

        elif self._policy_restricted.match(group_id):
            raise GroupPolicyException(
                "This group cannot be used in Canvas: %s" % group_id)

    def get_effective_members(self, group_id, act_as=None):
        self._gws.actas = act_as
        self._user_policy = UserPolicy()
        self._root_group_id = group_id
        (valid_members, invalid_members,
            member_groups) = self._get_members(group_id)
        return (valid_members.values(), invalid_members.values(),
                member_groups)

    def _get_members(self, group_id):
        valid_members = {}
        invalid_members = {}
        member_group_ids = []

        try:
            self.valid(group_id)
            group_members = self._gws.get_members(group_id)
            for member in group_members:
                try:
                    if member.is_uwnetid():
                        self._user_policy.valid_net_id(member.name)
                        valid_members[member.name] = member

                    elif member.is_eppn():
                        self._user_policy.valid_gmail_id(member.name)
                        valid_members[member.name] = member

                    elif member.is_group():
                        (valid_sub, invalid_sub,
                            member_subgroups) = self._get_members(member.name)
                        valid_members.update(valid_sub)
                        invalid_members.update(invalid_sub)
                        member_group_ids += [member.name] + member_subgroups

                except (GroupNotFoundException, GroupUnauthorizedException,
                        UserPolicyException, GroupPolicyException) as err:
                    member.error = err
                    invalid_members[member.name] = member

        except DataFailureException as err:
            # Group not found or access denied is ok
            if err.status == 404:
                raise GroupNotFoundException("Group not found: %s" % group_id)
            elif err.status == 401:
                raise GroupUnauthorizedException(
                    "Group not permitted for %s: %s" % (
                        self._gws.actas, group_id))
            else:
                raise

        except GroupPolicyException as err:
            raise

        return (valid_members, invalid_members, member_group_ids)


class CoursePolicy(object):
    def __init__(self):
        self._re_course_sis_id = re.compile(
            "^\d{4}-"                           # year
            "(?:winter|spring|summer|autumn)-"  # quarter
            "[\w& ]+-"                          # curriculum
            "\d{3}-"                            # course number
            "[A-Z][A-Z0-9]?"                    # section id
            "(?:-[A-F0-9]{32})?$",              # ind. study instructor regid
            re.VERBOSE)

        self._re_section_sis_id = re.compile(
            "^\d{4}-"                           # year
            "(?:winter|spring|summer|autumn)-"  # quarter
            "[\w& ]+-"                          # curriculum
            "\d{3}-"                            # course number
            "[A-Z](?:[A-Z0-9]|--)?$",           # section id
            re.VERBOSE)

        self._re_adhoc_sis_id = re.compile(r"^course_\d+$")
        self._re_canvas_id = re.compile(r"^\d+$")

    def valid_sis_id(self, sis_id):
        if not (sis_id and len(sis_id) > 0):
            raise CoursePolicyException("Invalid SIS Id")

    def valid_academic_course_sis_id(self, sis_id):
        if (self._re_course_sis_id.match(sis_id) is None):
            raise CoursePolicyException(
                "Invalid academic course SIS ID: %s" % sis_id)

    def valid_adhoc_course_sis_id(self, sis_id):
        if (self._re_adhoc_sis_id.match(sis_id) is None):
            raise CoursePolicyException("Invalid course SIS ID: %s" % sis_id)

    def valid_canvas_id(self, canvas_id):
        if (self._re_canvas_id.match(canvas_id) is None):
            raise CoursePolicyException("Invalid Canvas ID: %s" % canvas_id)

    def adhoc_sis_id(self, canvas_id):
        self.valid_canvas_id(canvas_id)
        return "course_%s" % canvas_id

    def valid_academic_section_sis_id(self, sis_id):
        if (self._re_section_sis_id.match(sis_id) is None):
            raise CoursePolicyException(
                "Invalid academic section SIS ID: %s" % sis_id)

    def group_section_sis_id(self, sis_id):
        self.valid_sis_id(sis_id)
        return "%s-groups" % sis_id

    def group_section_name(self):
        return getattr(settings, 'DEFAULT_GROUP_SECTION_NAME',
                       'UW Group members')

    def valid_canvas_section(self, section):
        course_id = section.canvas_course_sis_id()
        if (hasattr(section, "primary_lms") and section.primary_lms and
                section.primary_lms != Section.LMS_CANVAS):
            raise CoursePolicyException("Non-Canvas LMS '%s' for %s" % (
                section.primary_lms, course_id))
        else:
            try:
                override = SubAccountOverride.objects.get(course_id=course_id,
                                                          subaccount_id="NONE")
                raise CoursePolicyException("Not allowed: %s" % course_id)
            except SubAccountOverride.DoesNotExist:
                pass

    def is_active_section(self, section):
        try:
            self.valid_canvas_section(section)
            return not section.is_withdrawn
        except CoursePolicyException:
            return False

    def is_time_schedule_construction(self, section):
        campus = section.course_campus.lower()
        return next(
            (t.is_on for t in section.term.time_schedule_construction if (
                t.campus.lower() == campus)), False)

    def term_sis_id(self, section):
        try:
            override = TermOverride.objects.get(
                course_id=section.canvas_course_sis_id())
            return override.term_sis_id
        except TermOverride.DoesNotExist:
            pass

        if section.is_independent_start:
            return "uweo-individual-start"

        return section.term.canvas_sis_id()

    def term_name(self, section):
        try:
            override = TermOverride.objects.get(
                course_id=section.canvas_course_sis_id())
            return override.term_name
        except TermOverride.DoesNotExist:
            pass

        if section.is_independent_start:
            return "UWEO Individual Start"

        return " ".join([section.term.quarter.capitalize(),
                         str(section.term.year)])

    def term_start_date(self, section):
        if section.is_independent_start:
            return None
        else:
            return section.term.first_day_quarter

    def term_end_date(self, section):
        if section.is_independent_start:
            return None
        else:
            return section.term.grade_submission_deadline + timedelta(days=1)

    def canvas_account_id(self, section):
        course_id = section.canvas_course_sis_id()
        try:
            curr_abbr = section.curriculum_abbr
            curriculum = Curriculum.objects.get(curriculum_abbr=curr_abbr)
            account_id = curriculum.subaccount_id
        except Curriculum.DoesNotExist:
            account_id = None

        lms_owner_accounts = getattr(settings, 'LMS_OWNERSHIP_SUBACCOUNT', {})
        try:
            account_id = lms_owner_accounts[section.lms_ownership]
        except (AttributeError, KeyError):
            if account_id is None and section.course_campus == "PCE":
                account_id = lms_owner_accounts["PCE_NONE"]

        try:
            override = SubAccountOverride.objects.get(course_id=course_id)
            account_id = override.subaccount_id
        except SubAccountOverride.DoesNotExist:
            pass

        if account_id is None:
            raise CoursePolicyException("No account_id for %s" % course_id)

        return account_id

    def canvas_xlist_id(self, section_list):
        xlist_courses = []
        lms_ownership = {}
        for section in section_list:
            if section.canvas_course_sis_id() in getattr(
                    settings, 'LMS_XLIST_PRIMARY', []):
                lms_ownership[section] = section.lms_ownership
                section.lms_ownership = Section.LMS_OWNER_OL

            if self.is_active_section(section):
                xlist_courses.append(section)

        if not len(xlist_courses):
            return None

        xlist_courses.sort(key=lambda s: (
            s.lms_ownership != Section.LMS_OWNER_OL,
            s.canvas_course_sis_id())
        )

        for section in lms_ownership:
            section.lms_ownership = lms_ownership[section]

        return xlist_courses[0].canvas_course_sis_id()
