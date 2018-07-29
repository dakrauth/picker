#!/usr/bin/env python
import os, sys
from setuptools import find_packages, setup

setup(
    name='demo',
    url='https://github.com/dakrauth/picker/demo',
    author='David A Krauth',
    author_email='dakrauth@gmail.com',
    description='A Django sports picker app demo',
    version='0.1.0',
    long_description='See picker README.rst',
    platforms=['any'],
    license='MIT License',
    classifiers=(
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': ['demo=demo.__main__:main'],
    },

)
