# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import CourseCSV, SectionCSV, TermCSV, XlistCSV
from sis_provisioner.dao.course import (
    is_active_section, get_section_by_url, canvas_xlist_id, section_short_name,
    section_id_from_url)
from sis_provisioner.dao.canvas import (
    get_section_by_sis_id, get_sis_sections_for_course,
    get_unused_course_report_data)
from sis_provisioner.models.course import Course
from sis_provisioner.exceptions import CoursePolicyException
from restclients_core.exceptions import DataFailureException
from uw_sws.exceptions import InvalidCanvasIndependentStudyCourse
import csv
import re


class CourseBuilder(Builder):
    """
    Generates import data for Course models.
    """
    def _init_build(self, **kwargs):
        self.include_enrollment = kwargs.get('include_enrollment', True)

    def _process(self, course):
        if course.queue_id is not None:
            self.queue_id = course.queue_id

        # Primary sections only
        if course.primary_id:
            section_id = course.primary_id
        else:
            section_id = course.course_id

        try:
            section = self.get_section_resource_by_id(section_id)
        except Exception:
            return

        if section.is_independent_study:
            self._process_independent_study_section(section)

            # This handles ind. study sections that were initially created
            # in the sdb without the ind. study flag set
            if section.is_withdrawn():
                course.priority = course.PRIORITY_NONE
                course.save()
        else:
            self._process_primary_section(section)

    def _process_primary_section(self, section):
        """
        Generates the import data for a non-independent study primary section.
        Primary sections are added to courses, linked (secondary) sections are
        added to sections.
        """
        if section is None:
            return

        if not section.is_primary_section or section.is_independent_study:
            raise CoursePolicyException("Not a primary section: {}".format(
                section.section_label()))

        if not self.data.add(CourseCSV(section=section)):
            return

        self.data.add(TermCSV(section))
        Course.objects.update_status(section)

        course_id = section.canvas_course_sis_id()
        primary_instructors = section.get_instructors()

        if len(section.linked_section_urls):
            dummy_section_id = '{}--'.format(course_id)
            try:
                canvas_section = get_section_by_sis_id(dummy_section_id)
                # Section has linked sections, but was originally
                # provisioned with a dummy section, which will be removed
                self.logger.info(
                    'Removed dummy section for {}'.format(course_id))
                self.data.add(SectionCSV(
                    section_id=dummy_section_id,
                    course_id=course_id,
                    name=section_short_name(section),
                    status='deleted'))
            except DataFailureException as ex:
                pass

            for url in section.linked_section_urls:
                try:
                    linked_course_id = section_id_from_url(url)
                    linked_section = self.get_section_resource_by_id(
                        linked_course_id)
                    # Add primary section instructors to each linked section
                    self._process_linked_section(linked_section,
                                                 primary_instructors)
                except (DataFailureException, CoursePolicyException):
                    pass

        else:
            self.data.add(SectionCSV(section=section))

            if is_active_section(section):
                for instructor in primary_instructors:
                    self.add_teacher_enrollment_data(section, instructor)

                if self.include_enrollment:
                    self.add_registrations_by_section(section)

        # Check for linked sections already in the Course table
        for linked_course_id in Course.objects.get_linked_course_ids(
                course_id):
            try:
                linked_section = self.get_section_resource_by_id(
                    linked_course_id)
                self._process_linked_section(linked_section,
                                             primary_instructors)
            except (DataFailureException, CoursePolicyException):
                pass

        # Iterate over joint sections
        for url in section.joint_section_urls:
            try:
                joint_course_id = section_id_from_url(url)
                joint_section = self.get_section_resource_by_id(
                    joint_course_id)
                self._process_primary_section(joint_section)
            except (DataFailureException, CoursePolicyException,
                    InvalidCanvasIndependentStudyCourse):
                pass

        # Joint sections already joined to this section in the Course table
        for joint_course_id in Course.objects.get_joint_course_ids(course_id):
            try:
                joint_section = self.get_section_resource_by_id(
                    joint_course_id)
                self._process_primary_section(joint_section)
            except (DataFailureException, CoursePolicyException,
                    InvalidCanvasIndependentStudyCourse):
                pass

        self._process_xlists_for_section(section)

        # Find any sections that are manually cross-listed to this course,
        # so we can update enrollments for those
        try:
            canvas_sections = get_sis_sections_for_course(course_id)
        except DataFailureException:
            canvas_sections = []

        for s in canvas_sections:
            try:
                course_model_id = re.sub(r'--$', '', s.sis_section_id)
                course = Course.objects.get(course_id=course_model_id,
                                            queue_id__isnull=True)
                self._process(course)
            except Course.DoesNotExist:
                pass

    def _process_linked_section(self, section, primary_instructors=[]):
        """
        Generates the import data for a non-independent study linked section.
        Linked (secondary) sections are added to sections.
        """
        if section is None:
            return

        if section.is_primary_section or section.is_independent_study:
            raise CoursePolicyException(
                "Not a linked section: {}".format(section.section_label()))

        if self.data.add(SectionCSV(section=section)):
            if is_active_section(section):
                instructors = section.get_instructors()
                instructors.extend(primary_instructors)
                for instructor in instructors:
                    self.add_teacher_enrollment_data(section, instructor)

                if self.include_enrollment:
                    self.add_registrations_by_section(section)

            Course.objects.update_status(section)

    def _process_independent_study_section(self, section):
        """
        Generates the import data for an independent study section. This method
        will create course/section data for each instructor of the section,
        depending on whether section.independent_study_instructor_regid is set.
        """
        if section is None:
            return

        if not section.is_independent_study:
            raise CoursePolicyException(
                "Not an ind study section: {}".format(section.section_label()))

        match_independent_study = section.independent_study_instructor_regid
        for instructor in section.get_instructors():
            if (match_independent_study is not None and
                    match_independent_study != instructor.uwregid):
                continue

            section.independent_study_instructor_regid = instructor.uwregid

            if not self.data.add(CourseCSV(section=section)):
                continue

            self.data.add(TermCSV(section))
            self.data.add(SectionCSV(section=section))

            Course.objects.update_status(section)

            if is_active_section(section):
                self.add_teacher_enrollment_data(section, instructor)

                if self.include_enrollment:
                    self.add_registrations_by_section(section)

    def _process_xlists_for_section(self, section):
        """
        Generates the full xlist import data for the passed primary section.
        """
        if not section.is_primary_section or section.is_independent_study:
            raise CoursePolicyException(
                "Not a primary section: {}".format(section.section_label()))

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
                except Exception as err:
                    self.logger.info("Unable to xlist section {}: {}".format(
                        url, err))

            try:
                new_xlist_id = canvas_xlist_id(joint_sections)
            except Exception as err:
                self.logger.info(
                    "Unable to generate xlist_id for {}: {}".format(
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
            except DataFailureException:
                pass

        if not len(section.linked_section_urls):
            # Use the dummy section
            linked_section_ids.append(section.canvas_section_sis_id())

        for linked_section_id in linked_section_ids:
            if (existing_xlist_id is not None and
                    existing_xlist_id != new_xlist_id):
                self.data.add(XlistCSV(existing_xlist_id, linked_section_id,
                                       status='deleted'))

            if (new_xlist_id is not None and new_xlist_id != course_id):
                self.data.add(XlistCSV(new_xlist_id, linked_section_id,
                                       status='active'))


class UnusedCourseBuilder(Builder):
    def _init_build(self, **kwargs):
        self.term_sis_id = kwargs.get('term_sis_id')
        report_data = get_unused_course_report_data(self.term_sis_id)
        header = report_data.pop(0)
        for row in csv.reader(report_data):
            if len(row):
                self.items.append(row)

    def _process(self, row):
        course_id = row[1]
        if course_id is None or not len(course_id):
            return

        status = row[4]
        if status == 'unpublished':
            kwargs = {'course_id': course_id,
                      'short_name': row[2],
                      'long_name': row[3],
                      'account_id': None,
                      'term_id': self.term_sis_id,
                      'status': 'deleted'}

            self.data.add(CourseCSV(**kwargs))
