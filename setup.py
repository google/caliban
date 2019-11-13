from setuptools import find_packages
from setuptools import setup

setup(
    name='caliban',
    version='0.1',
    python_requires='>3.6.0',
    install_requires=[
        'absl-py', 'pyyaml', 'oauth2client', 'commentjson',
        'google-cloud-storage', 'google-api-python-client'
    ],
    extras_require={
        # These are required for local development, but not for actually running
        # the application.
        'dev': ['python-language-server[all]'],
    },
    packages=find_packages(),
    description='Docker-based job runner for AI research.',
    entry_points={'console_scripts': ['caliban = caliban.main:main']})
