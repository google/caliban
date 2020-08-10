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

REQUIRED_PACKAGES = [
    "alembic==1.4.2",
    "google-cloud-storage",
    'matplotlib',
    'mlflow==1.10.0',
    "pg8000==1.16.1",
    "sqlalchemy==1.3.13",
    'tensorflow-cpu',
    'tensorflow_datasets',
    'uv-metrics>=0.4.2',
]

setup(
    version="0.0.1",
    name='uv-metrics-tutorial',
    description='UV Metrics example.',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=REQUIRED_PACKAGES,
)
