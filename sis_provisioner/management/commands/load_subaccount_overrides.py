from django.core.management.base import BaseCommand
from optparse import make_option
from sis_provisioner.models import SubAccountOverride
from sis_provisioner.builders import Builder
from restclients.sws.section import get_joint_sections
from restclients.pws import PWS
import json
import sys
import re
import csv


class CourseTermException(Exception):
    pass


class Command(BaseCommand):
    help = "Load Course Sub Account Override list"

    option_list = BaseCommand.option_list + (
        make_option('--subaccount', dest='subaccount', default=False, help='Overriding subaccount'),
        make_option('--term', dest='term', default=False, help='Term id or JSON map of codes to course_id terms'),
        make_option('--verbose', dest='verbose', default=0, type='int', help='Verbose mode'),
        make_option('--delimiter', dest='delimiter', default=',', help='CSV file delimiter'),
        make_option('--quotechar', dest='quotechar', default='"', help='CSV file quote character'),
        make_option('--remove', action="store_true", dest='remove', default=False, help='remove course from subaccount override'),
        make_option('--reconcile', action="store_true", dest='reconcile', default=False, help='provided overrides are authoratative for contained quarter'),
    )

    _builder = Builder()

    _pws = PWS()

    # dictionary keys are CSV column headings, values are model field names
    _field_map = {
        'overrideLinked': 'override_linked',
        'termCd': 'term_code',
        'courseAbbrev': 'curriculum_code',
        'courseNo': 'course_number',
        'courseSection': 'course_section',
        'instructorEmployeeID': 'instructor_eid'
    }

    def handle(self, *args, **options):
        if options['verbose'] > 0:
            print >> sys.stderr, "delimiter is '{0}'".format(options['delimiter'])
            print >> sys.stderr, "quote character is '{0}'".format(options['quotechar'])

        if not options['subaccount']:
            print >> sys.stderr, "Missing overriding subbccount --subaccount"
            exit(1)

        if options['term']:
            if options['term'][0] == '{':
                term_map = json.loads(options['term'])
                term = lambda x:  term_map[x]
            else:
                term = lambda x: options['term']
        else:
            term = self._term

        data = []
        joint_courses = []
        if len(args) and args[0][1] != '-':

            current = None

            with open(args[0], 'r') as f:
                for row in csv.reader(f, delimiter=options['delimiter'], quotechar=options['quotechar']):
                    if len(data) == 0:
                        for label in row:
                            label = label.strip()

                            if label in self._field_map:
                                data.append({ 'field': self._field_map[label] })
                            else:
                                data.append({ 'field': label })
                                if options['verbose'] > 0:
                                    print >> sys.stderr, "Uknown column: '{0}'".format(label)
                    else:
                        columns = {}
                        for i in range(len(data)):
                            columns[data[i]['field']] = row[i].strip()

                        if options['reconcile']:
                            if current is None:
                                term = self._term(columns['term_code'])
                                current = list(SubAccountOverride.objects.filter(
                                            course_id__startswith=term).values_list('course_id', flat=True))

                        try:
                            if options['verbose'] > 2:
                                print >> sys.stderr, "'Line:"
                                for k,v in self._field_map.iteritems():
                                    print >> sys.stderr, '  {0} = {1}'.format(v, columns[v])

                            has_course_section = (len(columns['course_section']) > 0)

                            course_id = '-'.join([self._term(columns['term_code']),
                                                  columns['curriculum_code'],
                                                  columns['course_number'],
                                                  columns['course_section'] if has_course_section else '_' ])

                            # more than an ordinary class?
                            if has_course_section:
                                try:
                                    section = self._builder.get_section_resource_by_id(course_id)
                                    if "independent study" == section.section_type:
                                        try:
                                            course_id += '-' + self._pws.get_person_by_employee_id(columns['instructor_eid']).uwregid
                                        except:
                                            self._remove_override(course_id, options)
                                            if options['verbose'] > 0:
                                                print >> sys.stderr, 'Skipping: independent study: "{0}"'.format(course_id)

                                                continue

                                    joint = get_joint_sections(section)
                                    if len(joint) > 0:
                                        if course_id in joint_courses:
                                            if options['verbose'] > 1:
                                                print >> sys.stderr, 'course appears in joint list: {0}'.format(course_id)

                                            continue

                                        override = True if (columns.get('override_linked', 'false').lower() == 'true') else False
                                        if override:
                                            joint_courses.append(course_id)
                                        elif options['verbose'] > 0:
                                            print >> sys.stderr, 'Skipping: cross listed: {0}'.format(course_id)

                                        for s in joint:
                                            linked_course_id = re.sub(r"[,/]", '-', s.section_label())
                                            if override:
                                                joint_courses.append(linked_course_id)
                                                if options['remove']:
                                                    print >> sys.stderr, 'Removing cross listed course: "{0}"'.format(linked_course_id)
                                                    self._remove_override(linked_course_id, options)
                                                else:
                                                    print >> sys.stderr, 'Adding cross listed course: "{0}"'.format(linked_course_id)
                                                    self._update_override(linked_course_id, options)
                                                    if options['reconcile']:
                                                        try:
                                                            current.remove(linked_course_id)
                                                        except (AttributeError, ValueError): pass
                                            elif options['verbose'] > 1:
                                                print >> sys.stderr, '    with: {0}'.format(linked_course_id)

                                        if not override:
                                            continue
                                except:
                                    # not in sws, fall thru
                                    pass
                            else: # missing course section
                                # until non-credit courses appear
                                self._remove_override(course_id, options)
                                if options['verbose'] > 0:
                                    print >> sys.stderr, 'Skipping: missing course section: "{0}"'.format(course_id)

                                continue

                            if options['remove']:
                                self._remove_override(course_id, options)
                            else:
                                self._update_override(course_id, options)
                                if options['reconcile']:
                                    try:
                                        current.remove(course_id)
                                    except (AttributeError, ValueError): pass

                        except CourseTermException as err:
                            if options['verbose'] > 0:
                                print >> sys.stderr, 'Skipping: {0}'.format(err)

            if options['reconcile'] and current:
                for course_id in current:
                    if options['verbose'] > 0:
                        print >> sys.stderr, 'Reconcile removing: {0}'.format(course_id)

                    self._remove_override(course_id, options)

    def _update_override(self, course_id, options):
        try:
            override = SubAccountOverride.objects.get(course_id=course_id)
            override.subaccount_id = options['subaccount']
            if options['verbose'] > 0:
                print >> sys.stderr, 'Update override of |{0}| to "{1}"'.format(course_id, options['subaccount'])

        except SubAccountOverride.DoesNotExist:
            override = SubAccountOverride(course_id=course_id,
                                          subaccount_id=options['subaccount'])
            if options['verbose'] > 0:
                print >> sys.stderr, 'Set override of |{0}| to "{1}"'.format(course_id, options['subaccount'])

        override.save()


    def _remove_override(self, course_id, options):
        try:
            override = SubAccountOverride.objects.get(course_id=course_id)
            override.delete()
            if options['verbose'] > 0:
                print >> sys.stderr, 'Removed override: "{0}"'.format(course_id)

        except SubAccountOverride.DoesNotExist:
            pass

    def _get_regid_from_netid(self, netid):
        if not (netid and len(netid)):
            raise Exception("cannot get regid without netid")

        return 

    def _term(self, term_code):
        if re.match(r'^20[0-9]{2}0[1234]$', term_code):
            return "{0}-{1}".format(term_code[0:4],
                                    {'1': 'winter',
                                     '2': 'spring',
                                     '3': 'summer',
                                     '4': 'autumn'}[term_code[5:]])

        raise CourseTermException('Malformed term code "{0}"'.format(term_code))
