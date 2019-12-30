#!/usr/bin/env python
import os
import sys
from setuptools import find_packages, setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit(0)

with open('README.rst', 'r') as f:
    long_description = f.read()

# Dynamically calculate the version based on picker.VERSION.
version = __import__('picker').get_version()

setup(
    name='picker',
    url='https://github.com/dakrauth/picker',
    author='David A Krauth',
    author_email='dakrauth@gmail.com',
    description='A Django sports picker app',
    version=version,
    long_description=long_description,
    platforms=['any'],
    license='MIT License',
    install_requires=[
        'Django>=2.2.8,<3.0',
        'choice-enum==1.0.0',
        'django-bootstrap3>=12.0.1',
        'Pillow>=6.2.1',
        'python-dateutil>=2.8.1',
    ],
    extras_require={
        'test': ['tox',' coverage',' pytest-django',' pytest',' pytest-cov',' flake8'],
    },
    classifiers=(
        'License :: OSI Approved :: MIT License',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
