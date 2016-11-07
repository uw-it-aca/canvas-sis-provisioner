from django.conf import settings
from logging import getLogger
from django.utils.timezone import utc

from restclients.models.sws import Registration
from restclients.exceptions import DataFailureException,\
    InvalidCanvasIndependentStudyCourse

from sis_provisioner.dao.term import term_sis_id, get_term_by_year_and_quarter
from sis_provisioner.dao.course import canvas_xlist_id, is_active_section,\
    group_section_sis_id, get_section_by_id, get_section_by_url,\
    valid_academic_course_sis_id, valid_adhoc_course_sis_id,\
    get_registrations_by_section
from sis_provisioner.dao.canvas import get_course_by_id, get_course_by_sis_id,\
    update_course_sis_id, get_sis_sections_for_course,\
    get_sis_enrollments_for_course
from sis_provisioner.dao.group import get_effective_members
from sis_provisioner.dao.user import valid_net_id, valid_gmail_id,\
    get_person_by_gmail_id, get_person_by_netid, get_person_by_regid
from sis_provisioner.dao.account import get_all_campuses, get_all_colleges,\
    get_curricula_by_department, get_departments_by_college, account_sis_id,\
    account_name

from sis_provisioner.models import Course, Curriculum, Enrollment, Group,\
    CourseMember, GroupMemberGroup, PRIORITY_NONE, PRIORITY_DEFAULT
from sis_provisioner.exceptions import UserPolicyException,\
    MissingLoginIdException, CoursePolicyException, GroupPolicyException
from sis_provisioner.loader import load_user
from sis_provisioner.csv_data import CSVData

from sis_provisioner.csv_formatters import csv_for_user, csv_for_term,\
    csv_for_course, csv_for_section, csv_for_group_section,\
    csv_for_group_enrollment, csv_for_sis_instructor_enrollment,\
    csv_for_sis_student_enrollment, csv_for_xlist, csv_for_account,\
    header_for_accounts

from datetime import datetime
import re
import json


logger = getLogger(__name__)


class CSVBuilder():
    def __init__(self):
        self._csv = CSVData()
        self._queue_id = None
        self._invalid_users = {}

    def generate_csv_for_group_memberships(self, course_ids, delta=True):
        """
        Generates full csv for each of the passed course IDs.
        """
        course_ids = list(set(course_ids))
        cached_course_enrollments = {}
        for course_id in course_ids:
            try:
                try:
                    valid_adhoc_course_sis_id(course_id)
                    (prefix, canvas_course_id) = course_id.split('_')
                    canvas_course = get_course_by_id(canvas_course_id)
                except CoursePolicyException:
                    canvas_course = get_course_by_sis_id(course_id)

                if canvas_course.sis_course_id is None:
                    update_course_sis_id(canvas_course.course_id, course_id)
            except DataFailureException as err:
                if err.status == 404:
                    Group.objects.deprioritize_course(course_id)
                    logger.info("Drop group sync for deleted course %s" % (
                        course_id))
                    continue

            section_id = group_section_sis_id(course_id)
            if not self._csv.has_section(section_id):
                self._csv.add_section(section_id,
                                      csv_for_group_section(course_id))

            cached_members = CourseMember.objects.filter(course_id=course_id)
            current_members = []

            # Get the enrollments for academic courses from Canvas, excluding
            # ad-hoc and group sections
            try:
                valid_academic_course_sis_id(course_id)
                if course_id not in cached_course_enrollments:
                    canvas_enrollments = get_sis_enrollments_for_course(
                        course_id)
                    cached_course_enrollments[course_id] = canvas_enrollments

            except CoursePolicyException:
                canvas_enrollments = []
            except DataFailureException as err:
                Group.objects.dequeue_course(course_id)
                logger.info("Requeue group sync for course %s: %s" % (
                    course_id, err))
                continue

            groups = Group.objects.filter(course_id=course_id,
                                          is_deleted__isnull=True)
            try:
                for group in groups:
                    try:
                        (members, invalid_members,
                            member_groups) = get_effective_members(
                                group.group_id, act_as=group.added_by)

                        # remember member groups
                        for member_group_id in member_groups:
                            (gmg,
                             created) = GroupMemberGroup.objects.get_or_create(
                                group_id=member_group_id,
                                root_group_id=group.group_id)

                            if not created:
                                gmg.is_deleted = None
                                gmg.save()

                        # discard old member groups
                        for gmg in GroupMemberGroup.objects.filter(
                                root_group_id=group.group_id,
                                is_deleted__isnull=True):
                            if gmg.group_id not in member_groups:
                                gmg.is_deleted = True
                                gmg.save()

                        for member in invalid_members:
                            logger.info("Skip group member %s (%s)" % (
                                member.name, member.error))

                        for member in members:
                            login_id = member.name
                            if member.is_uwnetid():
                                user_id = member.name
                            elif member.is_eppn():
                                user_id = valid_gmail_id(member.name)
                            else:
                                continue

                            # Skip members already in academic course sections,
                            # removing from -group section
                            match = next((m for m in canvas_enrollments if (
                                m.login_id.lower() == member.name.lower())),
                                         None)
                            if match:
                                logger.info(
                                    "Skip group member %s (present in %s)" % (
                                        member.name, match.sis_section_id))
                                continue

                            course_member = CourseMember(
                                course_id=course_id,
                                name=user_id,
                                member_type=member.member_type,
                                role=group.role)
                            course_member.login = login_id
                            current_members.append(course_member)

                    except DataFailureException:
                        raise

                    # skip on any group policy exception
                    except GroupPolicyException as err:
                        logger.info("Skip group %s (%s)" % (
                            group.group_id, err))

            except DataFailureException as err:
                Group.objects.filter(course_id=course_id).update(queue_id=None)
                continue

            for member in cached_members:
                # Try to match on name, type, and role
                match = next((m for m in current_members if m == member), None)

                if match is None:
                    if not delta or not member.is_deleted:
                        self.generate_csv_for_groupmember(
                            member, section_id, member.role,
                            status=Enrollment.DELETED_STATUS)

                    member.is_deleted = True
                    member.deleted_date = datetime.utcnow().replace(tzinfo=utc)
                    member.save()

            for member in current_members:
                # Try to match on name, type, and role
                match = next((m for m in cached_members if m == member), None)

                # new or previously removed member
                if not delta or match is None or match.is_deleted:
                    self.generate_csv_for_groupmember(
                        member, section_id, member.role,
                        status=Enrollment.ACTIVE_STATUS)

                    if match is None:
                        member.save()
                    elif match.is_deleted:
                        match.is_deleted = None
                        match.deleted_date = None
                        match.save()

        return self._csv.write_files()

    def generate_csv_for_groupmember(self, member, section_id, role, status):
        if member.is_uwnetid():
            try:
                person = get_person_by_netid(member.name)
                self.generate_user_csv_for_person(person)

            except Exception as err:
                logger.info("Skip group member %s (%s)" % (
                    member.name, err))
                return

        elif member.is_eppn():
            if status == Enrollment.ACTIVE_STATUS and hasattr(member, "login"):
                person = get_person_by_gmail_id(member.login)
                if not self._csv.has_user(member.name):
                    self._csv.add_user(member.name, csv_for_user(person))
            else:
                person = get_person_by_gmail_id(member.name)
        else:
            return

        csv_data = csv_for_group_enrollment(section_id, person, role, status)
        self._csv.add_enrollment(csv_data)

    def generate_csv_for_enrollment_events(self, enrollments):
        """
        Generates full csv for each of the passed sis_provisioner.Enrollment
        objects.
        """
        for enrollment in enrollments:
            try:
                person = get_person_by_regid(enrollment.reg_id)

                section = self.get_section_resource_by_id(enrollment.course_id)
                section.independent_study_instructor_regid = (
                    enrollment.instructor_reg_id)

                if not is_active_section(section):
                    continue

            except MissingLoginIdException as err:
                self._requeue_enrollment_event(enrollment, err)
                continue
            except (UserPolicyException,
                    InvalidCanvasIndependentStudyCourse) as err:
                self._skip_enrollment_event(enrollment, err)
                continue
            except DataFailureException as err:
                if err.status == 404:
                    self._skip_enrollment_event(enrollment, err)
                else:
                    self._requeue_enrollment_event(enrollment, err)
                continue

            if enrollment.is_instructor():
                if section.is_independent_study:
                    # Add or remove independent study course
                    if not enrollment.is_active():
                        section.is_withdrawn = True

                    self._csv.add_course(section.canvas_course_sis_id(),
                                         csv_for_course(section))

                    if enrollment.is_active():
                        self._csv.add_section(
                            section.canvas_section_sis_id(),
                            csv_for_section(section))

                        csv_data = csv_for_sis_instructor_enrollment(
                            section, person, enrollment.status)
                        self._csv.add_enrollment(csv_data)

                elif len(section.linked_section_urls):
                    # Add/remove primary instructor for each linked section
                    for url in section.linked_section_urls:
                        try:
                            linked_section = get_section_by_url(url)
                        except Exception as err:
                            continue

                        csv_data = csv_for_sis_instructor_enrollment(
                            linked_section, person, enrollment.status)
                        self._csv.add_enrollment(csv_data)

                        self._csv.add_section(
                            linked_section.canvas_section_sis_id(),
                            csv_for_section(linked_section))

                else:
                    csv_data = csv_for_sis_instructor_enrollment(
                        section, person, enrollment.status)
                    self._csv.add_enrollment(csv_data)

                    self._csv.add_section(
                        section.canvas_section_sis_id(),
                        csv_for_section(section))

            else:  # student/auditor
                if len(section.linked_section_urls):
                    # Don't enroll students into primary sections
                    self._skip_enrollment_event(enrollment,
                                                'Section has linked sections')
                    continue

                registration = Registration(
                    section=section, person=person,
                    is_active=enrollment.is_active())
                csv_data = csv_for_sis_student_enrollment(registration)
                self._csv.add_enrollment(csv_data)

                self._csv.add_section(
                    section.canvas_section_sis_id(),
                    csv_for_section(section))

            # Add the user csv
            self.generate_user_csv_for_person(person)

        return self._csv.write_files()

    def _requeue_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = PRIORITY_DEFAULT
        enrollment.save()
        logger.info("Requeue enrollment %s in %s: %s" % (
            enrollment.reg_id, enrollment.course_id, err))

    def _skip_enrollment_event(self, enrollment, err):
        enrollment.queue_id = None
        enrollment.priority = PRIORITY_NONE
        enrollment.save()
        logger.info("Skip enrollment %s in %s: %s" % (
            enrollment.reg_id, enrollment.course_id, err))

    def generate_csv_for_course_members(self, course_members):
        """
        Generates the csv for each of the passed
        sis_provisioner.CourseMember objects.
        """
        for member in course_members:
            section_id = group_section_sis_id(member.course_id)
            status = Enrollment.DELETED_STATUS if (
                member.is_deleted) else Enrollment.ACTIVE_STATUS

            if member.is_eppn():
                member.login = member.name

            self.generate_csv_for_groupmember(member, section_id,
                                              member.role, status)

        return self._csv.write_files()

    def generate_course_csv(self, courses, include_enrollment=True):
        """
        Generates the full csv for each of the passed sis_provisioner.Course
        objects.
        """
        self._include_enrollment = include_enrollment
        self._process_course_models(courses)
        return self._csv.write_files()

    def _process_course_models(self, courses):
        for course in courses:
            if course.queue_id is not None:
                self._queue_id = course.queue_id

            # Primary sections only
            if course.primary_id:
                section_id = course.primary_id
            else:
                section_id = course.course_id

            try:
                section = self.get_section_resource_by_id(section_id)
            except:
                continue

            if course.primary_id:
                try:
                    Course.objects.add_to_queue(section, self._queue_id)
                except:
                    continue

            if section.is_independent_study:
                self.generate_independent_study_section_csv(section)

                # This handles ind. study sections that were initially created
                # in the sdb without the ind. study flag set
                if section.is_withdrawn:
                    course.priority = PRIORITY_NONE
                    course.save()
            else:
                self.generate_primary_section_csv(section)

    def generate_account_csv(self):
        """
        Generates the full csv for all sub-accounts found for the current
        term. Sub-account hierarchy is root account, campus, college,
        department, curriculum.
        """
        csv = self._csv
        root_id = getattr(settings, 'SIS_IMPORT_ROOT_ACCOUNT_ID', None)

        campuses = get_all_campuses()
        for campus in campuses:
            campus_id = account_sis_id([root_id, campus.label])

            if not csv.has_account(campus_id):
                csv_data = csv_for_account(campus_id, root_id, campus)
                csv.add_account(campus_id, csv_data)

        colleges = get_all_colleges()

        for college in colleges:
            college_id = account_sis_id([root_id, college.campus_label,
                                         college.name])

            if not csv.has_account(college_id):
                campus_id = account_sis_id([root_id, college.campus_label])
                csv_data = csv_for_account(college_id, campus_id, college)
                csv.add_account(college_id, csv_data)

            departments = get_departments_by_college(college)

            for dept in departments:
                dept_id = account_sis_id([root_id, college.campus_label,
                                          college.name, dept.label])

                if not csv.has_account(dept_id):
                    csv_data = csv_for_account(dept_id, college_id, dept)
                    csv.add_account(dept_id, csv_data)

                curricula = get_curricula_by_department(dept, future_terms=2)

                for curriculum in curricula:
                    curr_id = account_sis_id([root_id, college.campus_label,
                                              college.name, dept.label,
                                              curriculum.label])

                    if not csv.has_account(curr_id):
                        csv_data = csv_for_account(
                            curr_id, dept_id, curriculum)
                        csv.add_account(curr_id, csv_data)

                        # Update the Curriculum model for this curriculum
                        try:
                            model = Curriculum.objects.get(
                                curriculum_abbr=curriculum.label)
                        except Curriculum.DoesNotExist:
                            model = Curriculum(
                                curriculum_abbr=curriculum.label)

                        model.full_name = account_name(curriculum)
                        model.subaccount_id = curr_id
                        model.save()

        return csv.write_files()

    def generate_user_csv(self, users):
        """
        Generates the csv file for the passed users.
        """
        for user in users:
            try:
                person = get_person_by_netid(user.net_id)
                self.generate_user_csv_for_person(person, force=True)
            except UserPolicyException as err:
                logger.info("Skip user %s: %s" % (user.reg_id, err))

        return self._csv.write_files()

    def generate_independent_study_section_csv(self, section):
        """
        Generates the full csv for an independent study section. This method
        will create course/section csv for each instructor of the section,
        depending on whether section.independent_study_instructor_regid is set.
        """
        if section is None:
            return

        if not section.is_independent_study:
            raise Exception("Not an independent study section: %s" % (
                section.section_label()))

        csv = self._csv

        match_independent_study = section.independent_study_instructor_regid
        for instructor in section.get_instructors():
            if (match_independent_study is not None and
                    match_independent_study != instructor.uwregid):
                continue

            section.independent_study_instructor_regid = instructor.uwregid

            course_id = section.canvas_course_sis_id()
            if csv.has_course(course_id):
                continue

            term_id = term_sis_id(section)
            if not csv.has_term(term_id):
                csv.add_term(term_id, csv_for_term(section))

            csv.add_course(course_id, csv_for_course(section))

            Course.objects.update_status(section)

            section_id = section.canvas_section_sis_id()
            csv.add_section(section_id, csv_for_section(section))

            if is_active_section(section):
                self.generate_user_csv_for_person(instructor)
                if instructor.uwregid not in self._invalid_users:
                    logger.info("ADD instructor %s to %s" % (
                        instructor.uwregid, section_id))
                    csv_data = csv_for_sis_instructor_enrollment(
                        section, instructor, Enrollment.ACTIVE_STATUS)
                    csv.add_enrollment(csv_data)

                if self._include_enrollment:
                    self.generate_student_enrollment_csv(section)

    def generate_primary_section_csv(self, section):
        """
        Generates the full csv for a non-independent study primary section.
        Primary sections are added to courses.csv, linked (secondary)
        sections are added to sections.csv
        """
        if section is None:
            return

        if section.is_independent_study:
            raise Exception("Independent study section: %s" % (
                section.section_label()))

        if not section.is_primary_section:
            raise Exception("Not a primary section: %s" % (
                section.section_label()))

        csv = self._csv
        term_id = term_sis_id(section)
        if not csv.has_term(term_id):
            csv.add_term(term_id, csv_for_term(section))

        course_id = section.canvas_course_sis_id()
        if csv.has_course(course_id):
            return

        # Add the course csv
        csv.add_course(course_id, csv_for_course(section))

        Course.objects.update_status(section)

        primary_instructors = section.get_instructors()
        if len(section.linked_section_urls):
            for url in section.linked_section_urls:
                try:
                    linked_section = get_section_by_url(url)
                    Course.objects.add_to_queue(linked_section, self._queue_id)
                except:
                    continue

                # Add primary section instructors to each linked section
                self.generate_linked_section_csv(linked_section,
                                                 primary_instructors)
        else:
            section_id = section.canvas_section_sis_id()

            csv.add_section(section_id, csv_for_section(section))

            if is_active_section(section):
                self.generate_teacher_enrollment_csv(section)

                if self._include_enrollment:
                    self.generate_student_enrollment_csv(section)

        # Check for linked sections already in the Course table
        for linked_course_id in Course.objects.get_linked_course_ids(
                course_id):
            if csv.has_section(linked_course_id):
                continue

            try:
                linked_section = self.get_section_resource_by_id(
                    linked_course_id)
                Course.objects.add_to_queue(linked_section, self._queue_id)
                self.generate_linked_section_csv(linked_section,
                                                 primary_instructors)
            except Exception as ex:
                Course.objects.remove_from_queue(linked_course_id, ex)
                continue

        # Iterate over joint sections
        for url in section.joint_section_urls:
            try:
                joint_section = get_section_by_url(url)
                model = Course.objects.add_to_queue(joint_section,
                                                    self._queue_id)
            except:
                continue

            try:
                self.generate_primary_section_csv(joint_section)

            except Exception as ex:
                Course.objects.remove_from_queue(model.course_id, ex)
                continue

        # Joint sections already joined to this section in the Course table
        for joint_course_id in Course.objects.get_joint_course_ids(course_id):
            try:
                joint_section = self.get_section_resource_by_id(
                    joint_course_id)
                Course.objects.add_to_queue(joint_section, self._queue_id)
                self.generate_primary_section_csv(joint_section)

            except Exception as ex:
                Course.objects.remove_from_queue(joint_course_id, ex)
                continue

        self.generate_xlists_csv(section)

        # Find any sections that are manually cross-listed to this course,
        # so we can update enrollments for those
        course_models = []
        for s in get_sis_sections_for_course(course_id):
            if csv.has_section(s.sis_section_id):
                continue

            try:
                course_model_id = re.sub(r'--$', '', s.sis_section_id)
                course = Course.objects.get(course_id=course_model_id)
                course_models.append(course)
            except Course.DoesNotExist:
                continue

            self._process_course_models(course_models)

    def generate_linked_section_csv(self, section, primary_instructors):

        """
        Generates the full csv for a non-independent study linked section.
        Linked (secondary) sections are added to sections.csv
        """
        if section is None:
            return

        if section.is_independent_study:
            raise Exception("Independent study section: %s" % (
                section.section_label()))

        if section.is_primary_section:
            raise Exception("Not a linked section: %s" % (
                section.section_label()))

        csv = self._csv
        section_id = section.canvas_section_sis_id()
        if csv.has_section(section_id):
            return

        csv.add_section(section_id, csv_for_section(section))

        if is_active_section(section):
            self.generate_teacher_enrollment_csv(section, primary_instructors)

            if self._include_enrollment:
                self.generate_student_enrollment_csv(section)

        Course.objects.update_status(section)

    def generate_teacher_enrollment_csv(self, section, default_instructors=[]):
        """
        Generates the full teacher enrollments csv for the passed section.
        """
        instructors = section.get_instructors()
        instructors.extend(default_instructors)
        for person in instructors:
            self.generate_user_csv_for_person(person)

            if person.uwregid not in self._invalid_users:
                logger.info("ADD instructor %s to %s" % (
                    person.uwregid, section.canvas_section_sis_id()))
                csv_data = csv_for_sis_instructor_enrollment(
                    section, person, Enrollment.ACTIVE_STATUS)
                self._csv.add_enrollment(csv_data)

    def generate_student_enrollment_csv(self, section):
        """
        Generates the full student enrollments csv for the passed section.
        """
        for registration in get_registrations_by_section(section):
            # Add the student user csv
            self.generate_user_csv_for_person(registration.person)

            # Add the student enrollment csv
            if registration.person.uwregid not in self._invalid_users:
                csv_data = csv_for_sis_student_enrollment(registration)
                self._csv.add_enrollment(csv_data)

    def generate_xlists_csv(self, section):
        """
        Generates the full xlists csv for the passed primary section.
        """
        if not section.is_primary_section:
            raise Exception(
                "Not a primary section %s:" % section.section_label())

        if section.is_independent_study:
            raise Exception(
                "Independent study section %s:" % section.section_label())

        course_id = section.canvas_course_sis_id()

        try:
            model = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return

        existing_xlist_id = model.xlist_id
        new_xlist_id = None

        if len(section.joint_section_urls):
            joint_sections = [section]
            for url in section.joint_section_urls:
                try:
                    joint_sections.append(get_section_by_url(url))
                except DataFailureException:
                    continue

            try:
                new_xlist_id = canvas_xlist_id(joint_sections)
            except Exception as err:
                logger.info("Unable to generate xlist_id for %s: %s" % (
                    course_id, err))

        if existing_xlist_id is None and new_xlist_id is None:
            return

        if existing_xlist_id != new_xlist_id:
            model.xlist_id = new_xlist_id
            model.save()

        linked_section_ids = []
        for url in section.linked_section_urls:
            try:
                linked_section = get_section_by_url(url)
                linked_section_ids.append(
                    linked_section.canvas_section_sis_id())
            except:
                continue

        if not len(section.linked_section_urls):
            # Use the dummy section
            linked_section_ids.append(section.canvas_section_sis_id())

        for linked_section_id in linked_section_ids:
            if (existing_xlist_id is not None and
                    existing_xlist_id != new_xlist_id):
                self._csv.add_xlist(csv_for_xlist(existing_xlist_id,
                                                  linked_section_id,
                                                  status="deleted"))

            if (new_xlist_id is not None and new_xlist_id != course_id):
                self._csv.add_xlist(csv_for_xlist(new_xlist_id,
                                                  linked_section_id,
                                                  status="active"))

    def generate_user_csv_for_person(self, person, force=False):
        """
        Adds a line of csv for the passed person.  If force is not
        true, the csv will only be created if the person has not been
        provisioned.
        """
        csv = self._csv
        if (csv.has_user(person.uwregid) or
                person.uwregid in self._invalid_users):
            return

        try:
            valid_net_id(person.uwnetid)
        except UserPolicyException as err:
            self._invalid_users[person.uwregid] = True
            logger.info("Skip user %s: %s" % (person.uwregid, err))
            return

        if force is True:
            csv.add_user(person.uwregid, csv_for_user(person))
        else:
            user = load_user(person)
            if user.provisioned_date is None:
                csv.add_user(person.uwregid, csv_for_user(person))

                if user.queue_id is None:
                    user.queue_id = self._queue_id
                    user.save()

    def get_section_resource_by_id(self, section_id):
        """
        Fetch the section resource for the passed section ID.
        """
        try:
            return get_section_by_id(section_id)

        except DataFailureException as err:
            data = json.loads(err.msg)
            Course.objects.remove_from_queue(section_id, "%s: %s %s" % (
                err.url, err.status, data["StatusDescription"]))
            logger.info("Skip section %s: %s %s" % (
                section_id, err.status, data["StatusDescription"]))
            raise

        except ValueError as err:
            Course.objects.remove_from_queue(section_id, err)
            logger.info("Skip section %s: %s" % (section_id, err))
            raise
