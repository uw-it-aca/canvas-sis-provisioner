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
        'Django>=2.0.8,<2.1',
        'django-compressor',
        'django-user-agents',
        'lxml>=4.2.5,<4.3',
        'python-dateutil',
        'mock==2.0.0',
        'django-pyscss',
        'beautifulsoup4',
        'suds-jurko==0.6',
        'django-blti>=2.1.2,<3.0',
        'django-aws-message>=1.5.1',
        'UW-Canvas-Users-LTI>=0.8,<1.0',
        'UW-Groups-LTI>=0.7,<1.0',
        'UW-Course-Roster-LTI>=1.0,<2.0',
        'UW-Grading-Standard-LTI>=0.8,<1.0',
        'UW-Library-Guides-LTI>=0.6,<1.0',
        'Anonymous-Feedback-LTI>=0.3,<1.0',
        'UW-RestClients-Core>=1.1.1,<2.0',
        'UW-RestClients-SWS>=2.0.3,<3.0',
        'UW-RestClients-PWS>=2.0.2,<3.0',
        'UW-RestClients-GWS>=2.0.1,<3.0',
        'UW-RestClients-KWS>=1.0,<2.0',
        'UW-RestClients-Canvas>=1.1,<2.0',
        'UW-RestClients-Django-Utils>=2.1.4,<3.0',
        'Django-SupportTools>=3.3,<4.0',
        'UW-Django-SAML2>=1.3.8,<2.0',
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
        'Programming Language :: Python :: 3.6',
    ],
)
