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
        'Django==1.11.10',
        'urllib3==1.10.2',
        'lxml',
        'python-dateutil',
        'nameparser>=0.2.9',
        'mock==2.0.0',
        'django-compressor',
        'django-pyscss',
        'django-templatetag-handlebars',
        'django_mobileesp',
        'beautifulsoup4',
        'suds-jurko==0.6',
        'django-blti==1.2.5',
        'django-aws-message>=0.1,<1.0',
        'UW-Canvas-Users-LTI>=0.4,<1.0',
        'UW-Groups-LTI>=0.4,<1.0',
        'UW-Course-Roster-LTI>=0.5,<1.0',
        'UW-Grading-Standard-LTI>=0.5,<1.0',
        'UW-Library-Guides-LTI>=0.4,<1.0',
        'Anonymous-Feedback-LTI>=0.2.2,<1.0',
        'UW-RestClients-Core==0.9.6',
        'UW-RestClients-SWS>=1.5.1,<2.0',
        'UW-RestClients-PWS>=0.6,<1.0',
        'UW-RestClients-GWS>=1.0<2.0',
        'UW-RestClients-KWS>=0.1,<1.0',
        'UW-RestClients-Canvas>=0.7.1,<1.0',
        'UW-RestClients-Django-Utils>=0.7.2,<1.0',
        'Django-SupportTools>=1.3.1',
        'UW-Django-SAML2>=0.4.2',
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
