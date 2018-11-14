#!/usr/bin/env python

from setuptools import setup, find_packages


with open('README') as f:
    readme = f.read()


with open('LICENSE') as f:
    license = f.read()


setup(
    name='Smart Exporter',
    version='0.1',
    description='A smart exporter plugin for prometheus.',
    long_description=readme,
    author='Mike Liao',
    author_email='mike.liao@prophetstor.com',
    license=license,
    # packages=find_packages(exclude=('tests')),
    install_requires=[
        "prometheus_client"
    ],
    entry_points={
        'console_scripts': ['smart_exporter=smart_exporter.__init__:main'],
    },
    test_suite='tests',
    zip_safe=False
)

