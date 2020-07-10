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
"""unit tests for caliban history"""

from datetime import datetime

from sqlalchemy.engine.base import Engine

import pytest  # type: ignore
from caliban.history.types import (ContainerSpec, Experiment, ExperimentGroup,
                                   Job, JobSpec, Platform)
from caliban.history.util import get_mem_engine, session_scope
from caliban.util import current_user

# https://mypy.readthedocs.io/en/latest/jobning_mypy.html#missing-imports

# we create and exist session scopes here to test persistence


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('engine', [get_mem_engine()])
def test_container_spec(engine: Engine):

  spec = {
      'nogpu': True,
      'cloud_key': '/path/to/key.json',
      'image_tag': None,
      'dir': ['/extra/path0', '/extra/path2'],
      'base_dir': '/home/foo',
      'module': 'train.py'
  }

  def validate_spec(session) -> ContainerSpec:
    s = session.query(ContainerSpec).all()
    assert len(s) == 1
    s = s[0]
    assert s.spec == spec
    assert s.user == current_user()
    return s

  # basic creation
  with session_scope(engine) as session:
    s = ContainerSpec.get_or_create(session=session, spec=spec)
    session.add(s)

  # test persistence, then create experiment
  with session_scope(engine) as session:
    s = validate_spec(session)
    xg = ExperimentGroup()
    e = Experiment.get_or_create(xgroup=xg, container_spec=s)

  # test experiment parent-child relationship
  with session_scope(engine) as session:
    s = validate_spec(session)
    assert len(s.experiments) == 1
    assert s.experiments[0].container_spec.id == s.id


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('engine', [get_mem_engine()])
def test_experiment_group(engine: Engine):

  def verify_xg(session):
    xg = session.query(ExperimentGroup).all()
    assert len(xg) == 1
    xg = xg[0]
    return xg

  # basic creation
  with session_scope(engine) as session:
    xg = ExperimentGroup.get_or_create(session=session)
    session.add(xg)

  test_timestamp = datetime.now()

  # test experiment group addition/peristence, test duplicate
  with session_scope(engine) as session:
    xg = verify_xg(session)
    assert xg.created < test_timestamp
    new_xg = ExperimentGroup.get_or_create(session=session)

  # test get_or_create, then create new xg
  with session_scope(engine) as session:
    xg = verify_xg(session)
    new_xg = ExperimentGroup.get_or_create(session=session, name='new-xgroup')
    session.add(new_xg)

  # test getting recent experiment groups
  with session_scope(engine) as session:
    xg = session.query(ExperimentGroup).filter(
        ExperimentGroup.created > test_timestamp).all()
    assert len(xg) == 1
    xg = xg[0]
    assert xg.name == 'new-xgroup'


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('engine', [get_mem_engine()])
def test_experiment(engine: Engine):

  container_spec = {
      'nogpu': True,
      'cloud_key': '/path/to/key.json',
      'image_tag': None,
      'dir': ['/extra/path0', '/extra/path2'],
      'base_dir': '/home/foo',
      'module': 'train.py'
  }

  with session_scope(engine) as session:
    xg = ExperimentGroup(name='foo-xgroup')
    c = ContainerSpec.get_or_create(session=session, spec=container_spec)
    j = Experiment.get_or_create(
        xgroup=xg,
        container_spec=c,
        args=['arg0', '3', 'arg1'],
        kwargs={
            'k0': 1,
            'k1': 's'
        },
    )
    session.add(xg)

  # check basic persistence, then create duplicate experiment
  with session_scope(engine) as session:
    e = session.query(Experiment).all()
    assert len(e) == 1
    e = e[0]
    assert e.args == ['arg0', '3', 'arg1']
    assert e.kwargs == {'k0': 1, 'k1': 's'}
    assert e.xgroup.name == 'foo-xgroup'
    assert e.container_spec.spec == container_spec

    new_e = Experiment.get_or_create(
        xgroup=e.xgroup,
        container_spec=e.container_spec,
        args=['arg0', '3', 'arg1'],
        kwargs={
            'k0': 1,
            'k1': 's'
        },
    )
    session.add(new_e)

  # test that get_or_create worked as desired
  with session_scope(engine) as session:
    e = session.query(Experiment).all()
    assert len(e) == 1
    e = e[0]
    assert e.container_spec.spec == container_spec


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('engine', [get_mem_engine()])
def test_job_spec(engine: Engine):

  job_spec = {'a': 2, 'b': [0, 1, 2], 'c': {'x': 1, 'y': 'foo'}}
  container_spec = {
      'nogpu': True,
      'cloud_key': '/path/to/key.json',
      'image_tag': None,
      'dir': ['/extra/path0', '/extra/path2'],
      'base_dir': '/home/foo',
      'module': 'train.py'
  }

  def validate_spec(session) -> JobSpec:
    s = session.query(JobSpec).all()
    assert len(s) == 1
    s = s[0]
    assert s.platform == Platform.LOCAL
    assert s.spec == job_spec
    return s

  # test basic creation
  with session_scope(engine) as session:
    xg = ExperimentGroup.get_or_create(session=session)
    c = ContainerSpec.get_or_create(session=session, spec=container_spec)
    e = Experiment.get_or_create(xgroup=xg, container_spec=c)
    j = JobSpec.get_or_create(
        experiment=e,
        spec=job_spec,
        platform=Platform.LOCAL,
    )
    session.add(xg)

  # test basic persistence, then add duplicate
  with session_scope(engine) as session:
    s = validate_spec(session)

    session.add(
        JobSpec.get_or_create(
            experiment=s.experiment,
            spec=job_spec,
            platform=Platform.LOCAL,
        ))

  # test get_or_create, then create new spec
  with session_scope(engine) as session:
    s = validate_spec(session)

    session.add(
        JobSpec.get_or_create(
            experiment=s.experiment,
            spec=job_spec,
            platform=Platform.CAIP,
        ))

  # verify that new spec was peristed
  with session_scope(engine) as session:
    s = session.query(JobSpec).all()
    assert len(s) == 2
    assert s[0].spec == s[1].spec
    assert s[0].platform != s[1].platform


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('engine', [get_mem_engine()])
def test_job(engine: Engine):

  args = ['a', 4]
  kwargs = {'k0': 0, 'k1': 'xyz'}
  job_spec = {'a': 2, 'b': [0, 1, 2], 'c': {'x': 1, 'y': 'foo'}}
  container_spec = {
      'nogpu': True,
      'cloud_key': '/path/to/key.json',
      'image_tag': None,
      'dir': ['/extra/path0', '/extra/path2'],
      'base_dir': '/home/foo',
      'module': 'train.py'
  }

  # test basic job creation
  with session_scope(engine) as session:

    xg = ExperimentGroup()
    c = ContainerSpec.get_or_create(session=session, spec=container_spec)
    e = Experiment.get_or_create(
        xgroup=xg,
        container_spec=c,
        args=args,
        kwargs=kwargs,
    )

    jspec = JobSpec.get_or_create(
        experiment=e,
        spec=job_spec,
        platform=Platform.TEST,
    )

    job = Job(spec=jspec, container='container0', details={'job_id': 123})
    session.add(e)

  # test job persistence
  with session_scope(engine) as session:
    j = session.query(Job).all()
    assert len(j) == 1
    j = j[0]
    assert j.container == 'container0'
    assert j.experiment.args == args
    assert j.experiment.kwargs == kwargs
    assert j.spec.spec == job_spec
    assert j.details['job_id'] == 123
