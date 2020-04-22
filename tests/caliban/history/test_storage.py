"""unit tests for caliban history storage"""

import pytest  # type: ignore
# https://mypy.readthedocs.io/en/latest/running_mypy.html#missing-imports

import random
import uuid
import os

import hypothesis.strategies as st
from hypothesis import given, settings
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union, NewType
import re
import random
import pprint as pp
from datetime import datetime

from caliban.history.interfaces import (
    DictSerializable,
    Timestamped,
    Id,
    Named,
    User,
    Storage,
    Experiment,
    Job,
    Run,
    PlatformSpecific,
    QueryOp,
    ComputePlatform,
)

from caliban.history.null_storage import create_null_storage
from caliban.history.mem_storage import create_mem_storage
from caliban.history.firestore import create_firestore_storage
from caliban.history.null_compute import create_null_compute
from caliban.history.types import Platform, JobStatus
from caliban.types import Ignored, Ignore
import caliban.config as conf
from caliban.gke.utils import default_credentials

# define this environment variable to test against project firestore db
# note that this will create documents in the store
_FIRESTORE_PROJECT = os.environ.get('CALIBAN_TEST_FIRESTORE_PROJECT')


def get_firestore_storage() -> Optional[Storage]:
  if _FIRESTORE_PROJECT is None:
    return None

  return create_firestore_storage(_FIRESTORE_PROJECT,
                                  default_credentials().credentials)


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


def check_PlatformSpecific(p: PlatformSpecific, platform: Optional[Platform]):
  assert isinstance(p.platform(), Platform)
  if platform is not None:
    assert p.platform() == platform


# ----------------------------------------------------------------------------
def check_Job(
    job: Job,
    experiment: Experiment = None,
    name: Optional[str] = None,
    args: Union[Optional[List[str]], Ignored] = Ignore,
    kwargs: Union[Optional[Dict[str, Any]], Ignored] = Ignore,
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
def check_Run(r: Run,
              user: Optional[str] = None,
              platform: Optional[Platform] = None,
              job: Optional[Job] = None):
  assert r is not None

  check_DictSerializable(r)
  check_Timestamped(r)
  check_Id(r)
  check_User(r, user)
  check_PlatformSpecific(r, platform)

  assert r.status() is not None

  if job is not None:
    assert job.to_dict() == r.job().to_dict()

  return


# ----------------------------------------------------------------------------
def test_create_null_storage():
  '''simple creation test for null storage, which should always work'''
  assert create_null_storage() is not None


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', [
    create_null_storage(),
    create_mem_storage(),
    get_firestore_storage(),
])
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

  if s is None:
    return

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
@pytest.mark.parametrize('s', [
    create_mem_storage(),
    get_firestore_storage(),
])
def test_query_experiment(s: Storage):
  '''test experiment queries

  note that this does not work against a null-store'''

  if s is None:
    return

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
  assert exp_b is not None

  expcol = s.collection('experiments')
  assert expcol is not None

  all_exp = expcol.where('id', QueryOp.IN,
                         [e.id() for e in experiments] + [exp_b.id()])

  assert len(list(all_exp.execute())) == 5

  # get experiments by user
  user_a_experiments = list(
      all_exp.where('user', QueryOp.EQ, 'user_a').execute())

  assert len(user_a_experiments) == len(experiments)

  # check get/query for experiments
  for i in range(4):
    assert len(list(all_exp.execute())) == 5

    current = experiments[i].to_dict()

    # get by id
    assert current == expcol.get(experiments[i].id()).to_dict()

    # query by container name
    matches = list(
        all_exp.where('container', QueryOp.EQ, current['container']).execute())

    assert len(matches) == 1
    assert current == matches[0].to_dict()

  return


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', [
    create_mem_storage(),
    get_firestore_storage(),
])
def test_query_jobs(s: Storage):
  '''test job queries

  note that this does not work against a null-store'''

  if s is None:
    return

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
  expjobs = jobcol.where('experiment', QueryOp.IN,
                         [e.id() for e in experiments])

  # query jobs by experiment
  for e in experiments:
    # note job return ordering may vary, so we only have a single job/exp here
    assert list(e.jobs())[0].to_dict() == list(
        jobcol.where('experiment', QueryOp.EQ, e.id()).execute())[0].to_dict()

  # kwarg < query
  test_jobs = list(expjobs.where('kwargs.a', QueryOp.LT, 3).execute())

  assert len(test_jobs) == 3
  for j in test_jobs:
    assert j.kwargs()['a'] < 3

  # kwarg in query
  test_jobs = list(expjobs.where('kwargs.a', QueryOp.IN, [1, 2]).execute())

  assert len(test_jobs) == 2
  for j in test_jobs:
    assert j.kwargs()['a'] in [1, 2]

  # chanined query
  q = expjobs.where('kwargs.a', QueryOp.LT, 3)
  q = q.where('kwargs.a', QueryOp.IN, [1, 2, 3])

  test_jobs = list(q.execute())
  assert len(test_jobs) == 2
  for j in test_jobs:
    v = j.kwargs()['a']
    assert v < 3 and v in [1, 2, 3]


# ----------------------------------------------------------------------------
@pytest.mark.parametrize(
    's', [create_null_storage(),
          create_mem_storage(),
          get_firestore_storage()])
@pytest.mark.parametrize('c', [create_null_compute()])
def test_submit_jobs(s: Storage, c: ComputePlatform):

  if s is None:  # skip if backend is not being tested
    return

  num_jobs = 4

  exp = s.create_experiment(name='test-submit-exp',
                            container='test-submit-container',
                            command='cmd',
                            configs=[{
                                'a': i
                            } for i in range(num_jobs)],
                            args=None)

  assert exp is not None

  test_jobs = list(exp.jobs())
  test_runs = [j.submit(c) for j in test_jobs]

  assert len(test_runs) == num_jobs

  # check run validity
  for i in range(num_jobs):
    check_Run(test_runs[i], platform=c.platform(), job=test_jobs[i])

  # test cloning runs
  for i, r in enumerate(test_runs):
    j = test_jobs[i]
    cloned = r.clone()
    assert cloned is not None
    check_Run(cloned, platform=c.platform(), job=j)
    assert len(list(j.runs())) == 2


# ----------------------------------------------------------------------------
@pytest.mark.parametrize('s', [create_mem_storage()])
@pytest.mark.parametrize('c', [create_null_compute()])
def test_query_runs(s: Storage, c: ComputePlatform):

  if s is None:  # skip if backend is not being tested
    return

  num_jobs = 2
  exp = s.create_experiment(name='test-query-runs',
                            container='test-submit-container',
                            command='cmd',
                            configs=[{
                                'a': i
                            } for i in range(num_jobs)],
                            args=None)

  assert exp is not None

  test_jobs = list(exp.jobs())
  test_runs = [j.submit(c) for j in test_jobs]

  assert len(test_runs) == num_jobs

  for i, j in enumerate(test_jobs):
    query_runs = list(
        s.collection('runs').where('job', QueryOp.EQ, j.id()).execute())
    assert len(query_runs) == 1
    r = query_runs[0]
    check_Run(r, platform=c.platform(), job=j, user=test_runs[i].user())
