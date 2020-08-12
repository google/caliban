#!/usr/bin/python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import find_packages, setup


def with_versioneer(f, default=None):
  """Attempts to execute the supplied single-arg function by passing it
versioneer if available; else, returns the default.

  """
  try:
    import versioneer
    return f(versioneer)
  except ModuleNotFoundError:
    return default


def readme():
  try:
    with open('README.md') as f:
      return f.read()
  except Exception:
    return None


REQUIRED_PACKAGES = [
    'absl-py',
    'blessings',
    'commentjson',
    'google-api-python-client',
    'pyyaml',
    'tqdm>=4.45.0',
    'kubernetes>=10.0.1',
    'google-auth>=1.19.0',
    'google-cloud-core>=1.0.3',
    'google-cloud-container>=0.3.0',
    'psycopg2-binary==2.8.5',
    'schema==0.7.2',
    'urllib3>=1.25.7',
    'yaspin>=0.16.0',
    # This is not a real dependency of ours, but we need it to override the
    # dep that commentjson brings in. Delete once this is merged:
    # https://github.com/vaidik/commentjson/pull/33/files
    'lark-parser>=0.7.1,<0.8.0',
    'SQLAlchemy==1.3.11',
    'pg8000==1.16.1',
]

setup(name='caliban',
      version=with_versioneer(lambda v: v.get_version()),
      cmdclass=with_versioneer(lambda v: v.get_cmdclass(), {}),
      description='Docker-based job runner for AI research.',
      long_description=readme(),
      long_description_content_type="text/markdown",
      python_requires='>=3.6.0',
      author='Caliban Team',
      author_email='samritchie@google.com',
      url='https://github.com/google/caliban',
      license='Apache-2.0',
      packages=find_packages(exclude=('tests', 'docs')),
      install_requires=REQUIRED_PACKAGES,
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'caliban = caliban.main:main',
              'expansion = caliban.expansion:main'
          ]
      })
