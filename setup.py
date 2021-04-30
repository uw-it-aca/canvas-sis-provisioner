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
    install_requires = [
        'Django~=2.2',
        'django-compressor',
        'django-user-agents',
        'lxml>=4.2.5,<4.3',
        'python-dateutil',
        'django-pyscss>=2.0',
        'beautifulsoup4',
        'suds-jurko==0.6',
        'django-blti~=2.2',
        'django-aws-message~=1.5',
        'djangorestframework~=3.11,<3.12',
        'django-storages[google]>=1.10',
        'uw-memcached-clients~=1.0',
        'UW-RestClients-Core~=1.3',
        'UW-RestClients-SWS~=2.3',
        'UW-RestClients-PWS~=2.1',
        'UW-RestClients-GWS~=2.3',
        'UW-RestClients-KWS~=1.1',
        'UW-RestClients-Canvas>=1.1.17',
        'UW-RestClients-Django-Utils~=2.2',
        'Django-SupportTools~=3.5',
        'UW-Django-SAML2~=1.5',
        'prometheus-client>=0.7,<1.0',
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
