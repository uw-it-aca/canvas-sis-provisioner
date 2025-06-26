#!/usr/bin/env python

import os
from setuptools import setup

README = """
See the README on `GitHub
<https://github.com/uw-it-aca/canvas_sis_provisioner>`_.
"""

version_path = 'sis_provisioner/VERSION'
VERSION = open(os.path.join(os.path.dirname(__file__), version_path)).read()
VERSION = VERSION.replace("\n", "")

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='Canvas SIS Provisioner',
    version=VERSION,
    packages=['sis_provisioner'],
    include_package_data=True,
    install_requires=[
        'django~=5.2',
        'django-compressor',
        'django-user-agents',
        'python-dateutil',
        'django-pyscss>=2.0',
        'beautifulsoup4',
        'suds-py3~=1.4',
        'django-blti~=2.2',
        'django-cors-headers',
        'aws-message-client~=1.6',
        'djangorestframework~=3.14',
        'django-storages[google]',
        'uw-memcached-clients~=1.0',
        'uw-restclients-core~=1.4',
        'uw-restclients-sws>=2.4',
        'uw-restclients-pws~=2.1',
        'uw-restclients-gws~=2.3',
        'uw-restclients-kws~=1.1',
        'uw-restclients-canvas~=1.2',
        'uw-restclients-django-utils~=2.3',
        'django-supporttools~=3.6',
        'uw-django-saml2~=1.8',
        'prometheus-client>=0.7,<1.0',
    ],
    license='Apache License, Version 2.0',
    description='An application that manages SIS imports to Canvas',
    long_description=README,
    url='https://github.com/uw-it-aca/canvas-sis-provisioner',
    author="UW-IT Student & Educational Technology Services",
    author_email="aca-it@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
