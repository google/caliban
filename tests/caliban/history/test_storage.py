"""unit tests for caliban history storage"""

import pytest  # type: ignore
# https://mypy.readthedocs.io/en/latest/running_mypy.html#missing-imports

import random
import uuid

import hypothesis.strategies as st
from hypothesis import given, settings
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union, NewType
import re
import random
import pprint as pp
from datetime import datetime

from caliban.history.interfaces import (DictSerializable, Timestamped, Id,
                                        Named, User, Storage, Experiment, Job,
                                        Run, PlatformSpecific, QueryOp)

from caliban.history.null_storage import create_null_storage
from caliban.history.mem_storage import create_mem_storage
from caliban.types import Ignored, Ignore
import caliban.config as conf

_STORAGE_BACKENDS = [create_null_storage(), create_mem_storage()]


# ----------------------------------------------------------------------------
def check_Named(n: Named, name: Optional[str] = None):
  assert isinstance(n.name(), str)
  if name is not None:
    assert n.name() == name


def check_DictSerializable(s: DictSerializable):
  assert isinstance(s.to_dict(), dict)


def check_Timestamped(t: Timestamped, ts: Optional[datetime] = None):
  assert isinstance(t.timestamp(), datetime)
  if ts is not None:
    assert t.timestamp() == ts


def check_Id(x: Id, id: Optional[str] = None):
  assert isinstance(x.id(), str)
  if id is not None:
    assert x.id() == id


def check_User(u: User, user: Optional[str] = None):
  assert isinstance(u.user(), str)
  if user is not None:
    assert u.user() == user


# ----------------------------------------------------------------------------
def check_Job(
    job: Job,
    experiment: Experiment = None,
    name: Optional[str] = None,
    args: Union[Optional[List[str]], Ignored] = Ignore,
    kwargs: Union[Optional[Dict[str, str]], Ignored] = Ignore,
):
  check_DictSerializable(job)
  check_Timestamped(job)
  check_Id(job)
  check_Named(job, name)
  check_User(job)

  if experiment is not None:
    assert job.experiment().to_dict() == experiment.to_dict()

  if args is not None:
    assert job.args() == args
  else:
    assert job.args() == []

  if not isinstance(kwargs, Ignored):
    if kwargs is not None:
      assert job.kwargs() == kwargs
    else:
      assert job.kwargs() == {}


# ----------------------------------------------------------------------------
def check_Experiment(
    exp: Experiment,
    name: Optional[str] = None,
    container: Optional[str] = None,
    command: Union[Optional[str], Ignored] = Ignore,
    configs: Union[Optional[List[conf.Experiment]], Ignored] = Ignore,
    args: Union[Optional[List[str]], Ignored] = Ignore,
    user: Optional[str] = None,
):
  check_Named(exp, name)
  check_DictSerializable(exp)
  check_Timestamped(exp)
  check_Id(exp)
  check_User(exp, user)

  assert isinstance(exp.container(), str)
  if container is not None:
    assert exp.container() == container

  assert (isinstance(exp.command(), str) or (exp.command() is None))
  if command != Ignore:
    assert exp.command() == command

  assert exp.jobs() is not None

  job_count = 0
  for j in exp.jobs():
    job_count += 1

  if not isinstance(configs, Ignored):
    if configs is not None:
      num_jobs = len(configs)
      assert job_count == len(configs)

      if job_count == 1:
        check_Job(
            j,
            experiment=exp,
            args=args,
            kwargs={k: v for k, v in configs[0].items()},
        )
      else:  # don't check kwargs, as ordering in not necessarily consistent
        for i, j in enumerate(exp.jobs()):
          check_Job(
              j,
              experiment=exp,
              args=args,
          )
    else:
      assert job_count == 1
      check_Job(j, experiment=exp, args=args, kwargs=None)


# ----------------------------------------------------------------------------
def test_create_null_storage():
  '''simple creation test for null storage, which should always work'''
  assert create_null_storage() is not None


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', _STORAGE_BACKENDS)
@pytest.mark.parametrize('name', ['foo'])
@pytest.mark.parametrize('command', [None, 'cmd_a'])
@pytest.mark.parametrize('container', [uuid.uuid1().hex])
@pytest.mark.parametrize('configs', [
    None,
    [{
        'arg0': '0',
        'arg1': 'abc'
    }, {
        'a': 4,
        'b': False
    }],
    [{
        'x': 2
    }],
])
@pytest.mark.parametrize('args', [None, ['--verbose', '42']])
@pytest.mark.parametrize('user', [None, 'user_foo'])
def test_create_experiment(
    s: Storage,
    name: str,
    command: Optional[str],
    container: str,
    configs: Optional[List[conf.Experiment]],
    args: Optional[List[str]],
    user: str,
):
  '''test creating an experiment for storage backends'''

  exp = s.create_experiment(
      name=name,
      container=container,
      command=command,
      configs=configs,
      args=args,
      user=user,
  )

  assert exp is not None

  check_Experiment(exp,
                   name=name,
                   container=container,
                   command=command,
                   configs=configs,
                   args=args,
                   user=user)
  return


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', [create_mem_storage()])
def test_query_experiment(s: Storage):

  experiments = [
      s.create_experiment(name='exp-{}'.format(i),
                          container='container-{}'.format(i),
                          command='cmd',
                          configs=[{
                              'a': i
                          }],
                          args=None,
                          user='user_a') for i in range(4)
  ]

  exp_b = s.create_experiment(name='exp-b',
                              container='container-b',
                              command='cmd',
                              user='user_b')

  expcol = s.collection('experiments')

  # get experiments by user
  user_a_experiments = list(
      expcol.where('user', QueryOp.EQ, 'user_a').execute())

  assert len(user_a_experiments) == len(experiments)

  # check get/query for experiments
  for i in range(4):
    current = experiments[i].to_dict()

    # get by id
    assert current == expcol.get(experiments[i].id()).to_dict()

    # query by container name
    matches = list(
        expcol.where('container', QueryOp.EQ, current['container']).execute())

    assert len(matches) == 1
    assert current == matches[0].to_dict()

  return


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', [create_mem_storage()])
def test_query_jobs(s: Storage):

  experiments = [
      s.create_experiment(name='exp-{}'.format(i),
                          container='container-{}'.format(i),
                          command='cmd',
                          configs=[{
                              'a': i
                          }],
                          args=None,
                          user='user_a') for i in range(4)
  ]

  jobcol = s.collection('jobs')

  # query jobs by experiment
  for e in experiments:
    # note job return ordering may vary, so we only have a single job/exp here
    assert list(e.jobs())[0].to_dict() == list(
        jobcol.where('experiment', QueryOp.EQ, e.id()).execute())[0].to_dict()

  # kwarg < query
  test_jobs = list(jobcol.where('kwargs.a', QueryOp.LT, 3).execute())

  assert len(test_jobs) == 3
  for j in test_jobs:
    assert j.kwargs()['a'] < 3

  # kwarg in query
  test_jobs = list(jobcol.where('kwargs.a', QueryOp.IN, [1, 2]).execute())

  assert len(test_jobs) == 2
  for j in test_jobs:
    assert j.kwargs()['a'] in [1, 2]

  # chanined query
  q = jobcol.where('kwargs.a', QueryOp.LT, 3)
  q = q.where('kwargs.a', QueryOp.IN, [1, 2, 3])

  test_jobs = list(q.execute())
  assert len(test_jobs) == 2
  for j in test_jobs:
    v = j.kwargs()['a']
    assert v < 3 and v in [1, 2, 3]
