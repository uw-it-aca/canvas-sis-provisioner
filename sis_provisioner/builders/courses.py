from sis_provisioner.builders import Builder
from sis_provisioner.csv.format import CourseCSV, SectionCSV, TermCSV, XlistCSV
from sis_provisioner.dao.course import (
    is_active_section, get_section_by_url, canvas_xlist_id,
    get_registrations_by_section)
from sis_provisioner.models import Course, PRIORITY_NONE
import re


class CourseBuilder(Builder):
    """
    Generates import data for Course models.
    """
    def __init__(self, courses, include_enrollment=True):
        super(Builder, self).__init__()
        self.courses = courses
        self.include_enrollment = include_enrollment

    def _process_courses(courses):
        for course in courses:
            if course.queue_id is not None:
                self.queue_id = course.queue_id

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
                    Course.objects.add_to_queue(section, self.queue_id)
                except:
                    continue

            if section.is_independent_study:
                self.add_data_for_independent_study_section(section)

                # This handles ind. study sections that were initially created
                # in the sdb without the ind. study flag set
                if section.is_withdrawn:
                    course.priority = PRIORITY_NONE
                    course.save()
            else:
                self.add_data_for_primary_section(section)

    def add_data_for_primary_section(self, section):
        """
        Generates the import data for a non-independent study primary section.
        Primary sections are added to courses, linked (secondary) sections are
        added to sections.
        """
        if section is None:
            return

        if section.is_independent_study:
            raise Exception("Independent study section: %s" % (
                section.section_label()))

        if not section.is_primary_section:
            raise Exception("Not a primary section: %s" % (
                section.section_label()))

        self.data.add(TermCSV(section))
        if not self.data.add(CourseCSV(section=section)):
            return

        Course.objects.update_status(section)

        course_id = section.canvas_course_sis_id()
        primary_instructors = section.get_instructors()
        if len(section.linked_section_urls):
            for url in section.linked_section_urls:
                try:
                    linked_section = get_section_by_url(url)
                    Course.objects.add_to_queue(linked_section, self.queue_id)
                except:
                    continue

                # Add primary section instructors to each linked section
                self.add_data_for_linked_section(linked_section,
                                                 primary_instructors)
        else:
            self.data.add(SectionCSV(section=section))

            if is_active_section(section):
                for instructor in primary_instructors:
                    self.add_teacher_enrollment_data(section, instructor)

                if self.include_enrollment:
                    for registration in get_registrations_by_section(section):
                        self.add_student_enrollment_data(registration)

        # Check for linked sections already in the Course table
        for linked_course_id in Course.objects.get_linked_course_ids(
                course_id):
            try:
                linked_section = self.get_section_resource_by_id(
                    linked_course_id)
                Course.objects.add_to_queue(linked_section, self.queue_id)
                self.add_data_for_linked_section(linked_section,
                                                 primary_instructors)
            except Exception as ex:
                Course.objects.remove_from_queue(linked_course_id, ex)
                continue

        # Iterate over joint sections
        for url in section.joint_section_urls:
            try:
                joint_section = get_section_by_url(url)
                model = Course.objects.add_to_queue(joint_section,
                                                    self.queue_id)
            except:
                continue

            try:
                self.add_data_for_primary_section(joint_section)
            except Exception as ex:
                Course.objects.remove_from_queue(model.course_id, ex)

        # Joint sections already joined to this section in the Course table
        for joint_course_id in Course.objects.get_joint_course_ids(course_id):
            try:
                joint_section = self.get_section_resource_by_id(
                    joint_course_id)
                Course.objects.add_to_queue(joint_section, self.queue_id)
                self.add_data_for_primary_section(joint_section)

            except Exception as ex:
                Course.objects.remove_from_queue(joint_course_id, ex)

        self.add_xlist_data_for_section(section)

        # Find any sections that are manually cross-listed to this course,
        # so we can update enrollments for those
        course_models = []
        for s in get_sis_sections_for_course(course_id):
            try:
                course_model_id = re.sub(r'--$', '', s.sis_section_id)
                course = Course.objects.get(course_id=course_model_id,
                                            queue_id__isnull=True)
                course_models.append(course)
            except Course.DoesNotExist:
                pass

        self._process_courses(course_models)

    def add_data_for_linked_section(self, section, primary_instructors=[]):

        """
        Generates the import data for a non-independent study linked section.
        Linked (secondary) sections are added to sections.
        """
        if section is None:
            return

        if section.is_independent_study:
            raise Exception("Independent study section: %s" % (
                section.section_label()))

        if section.is_primary_section:
            raise Exception("Not a linked section: %s" % (
                section.section_label()))

        if self.data.add(SectionCSV(section=section)):
            if is_active_section(section):
                instructors = section.get_instructors()
                instructors.extend(primary_instructors)
                for instructor in instructors:
                    self.add_teacher_enrollment_data(section, instructor)

                if self.include_enrollment:
                    for registration in get_registrations_by_section(section):
                        self.add_student_enrollment_data(registration)

            Course.objects.update_status(section)

    def add_data_for_independent_study_section(self, section):
        """
        Generates the import data for an independent study section. This method
        will create course/section data for each instructor of the section,
        depending on whether section.independent_study_instructor_regid is set.
        """
        if section is None:
            return

        if not section.is_independent_study:
            raise Exception("Not an independent study section: %s" % (
                section.section_label()))

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
                    for registration in get_registrations_by_section(section):
                        self.add_student_enrollment_data(registration)

    def add_xlist_data_for_section(self, section):
        """
        Generates the full xlist import data for the passed primary section.
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
                    pass

            try:
                new_xlist_id = canvas_xlist_id(joint_sections)
            except Exception as err:
                self.logger.info("Unable to generate xlist_id for %s: %s" % (
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

    def build(self):
        self._process_courses(self.courses)
        return self.write()
