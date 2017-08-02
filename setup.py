#!/usr/bin/env python

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='canvas-sis-provisioner',
    version='1.0',
    packages=['sis_provisioner'],
    include_package_data=True,
    install_requires = [
        'Django==1.10.5',
        'urllib3==1.10.2',
        'lxml',
        'python-dateutil',
        'nameparser>=0.2.9',
        'mock==2.0.0',
        'django-compressor',
        'django-templatetag-handlebars',
        'beautifulsoup4',
        'suds-jurko==0.6',
        'django-userservice==1.2.1',
        'AuthZ-Group',
        'django-blti==0.2',
        'django-aws-message>=0.1,<1.0',
        'UW-Canvas-Users-LTI>=0.2.1,<1.0',
        'UW-Groups-LTI>=0.2.3,<1.0',
        'UW-Course-Roster-LTI>=0.2.2,<1.0',
        'UW-Grading-Standard-LTI>=0.2.3,<1.0',
        'UW-Library-Guides-LTI>=0.2.1,<1.0',
        'UW-RestClients-SWS>=1.0,<2.0',
        'UW-RestClients-PWS>=0.5,<1.0',
        'UW-RestClients-GWS>=0.3,<1.0',
        'UW-RestClients-KWS>=0.1,<1.0',
        'UW-RestClients-Canvas>=0.6.4,<1.0',
        'UW-RestClients-Django-Utils>=0.6.5,<1.0',
        'Django-SupportTools>=1.1',
        'django_mobileesp',
    ],
    license='Apache License, Version 2.0',
    description='An application that manages SIS imports to Canvas',
    long_description=README,
    url='https://github.com/uw-it-aca/canvas-sis-provisioner',
    author = "UW-IT AXDD",
    author_email = "aca-it@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
)
