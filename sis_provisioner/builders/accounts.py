# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from sis_provisioner.builders import Builder
from sis_provisioner.models import Curriculum
from sis_provisioner.csv.format import AccountCSV
from sis_provisioner.dao.account import (
    get_all_campuses, get_all_colleges, get_curricula_by_department,
    get_departments_by_college, account_sis_id, account_name)
from django.conf import settings


class AccountBuilder(Builder):
    """
    Generates the data for all sub-accounts found for the current
    term. Sub-account hierarchy is root account, campus, college,
    department, curriculum.
    """
    def build(self, **kwargs):
        root_id = getattr(settings, 'SIS_IMPORT_ROOT_ACCOUNT_ID', None)

        for campus in get_all_campuses():
            campus_id = account_sis_id([root_id, campus.label])
            self.data.add(AccountCSV(campus_id, root_id, campus))

        for college in get_all_colleges():
            college_id = account_sis_id([root_id, college.campus_label,
                                         college.name])
            campus_id = account_sis_id([root_id, college.campus_label])
            self.data.add(AccountCSV(college_id, campus_id, college))

            for department in get_departments_by_college(college):
                dept_id = account_sis_id([root_id, college.campus_label,
                                          college.name, department.label])

                self.data.add(AccountCSV(dept_id, college_id, department))

                for curriculum in get_curricula_by_department(
                        department, future_terms=2, view_unpublished=True):
                    curr_id = account_sis_id([root_id, college.campus_label,
                                              college.name, department.label,
                                              curriculum.label])

                    if self.data.add(AccountCSV(curr_id, dept_id, curriculum)):
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

        return self._write()
