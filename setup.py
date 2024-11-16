#!/usr/bin/env python
from setuptools import find_packages, setup


with open("README.rst", "r") as f:
    long_description = f.read()

# Dynamically calculate the version based on picker.VERSION.
version = __import__("picker").get_version()

setup(
    name="picker",
    url="https://github.com/dakrauth/picker",
    author="David A Krauth",
    author_email="dakrauth@gmail.com",
    description="A Django sports picker app",
    version=version,
    long_description=long_description,
    platforms=["any"],
    license="MIT License",
    install_requires=[
        "Django>=4.2",
        "django-bootstrap5",
        "Pillow>=6.2.1",
        "python-dateutil>=2.8.1",
    ],
    extras_require={
        "test": [
            "tox",
            "coverage",
            "pytest-django",
            "pytest",
            "pytest-cov",
            "flake8",
        ],
    },
    classifiers=(
        "License :: OSI Approved :: MIT License",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
