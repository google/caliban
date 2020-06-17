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
'''types for caliban.history'''

import json
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import sqlalchemy
from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String)
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, backref, relationship, sessionmaker
from sqlalchemy.orm.session import object_session

from caliban.util import current_user

# ----------------------------------------------------------------------------
# A note on JSON columns here:
# Currently sqlite supports JSON column comparisons in query filters, so
# you can query something along the lines of:
#   Query(Foo).filter(Bar.json_column == {'a':4})
# Postgres supportst this as well, but *only* for JSONB columns. Thus in order
# to use both sqlite and postgres backends you must stick to JSON columns,
# and when doing comparisons, use filter experssions of the form:
#   Query(Foo).filter(Bar.json_column.cast(String) == json.dumps({'a':4}))
# The danger here of course is that if the json serialization is inconsistent,
# then the above query will fail. As of this writing (2020.05.15), the
# psycopg2 driver for postgres uses python's default json.dumps() as its
# serializer, so this practice should be ok.


# ----------------------------------------------------------------------------
class JobStatus(str, Enum):
  '''job status'''
  SUBMITTED = 'SUBMITTED'
  RUNNING = 'RUNNING'
  SUCCEEDED = 'SUCCEEDED'
  FAILED = 'FAILED'
  STOPPED = 'STOPPED'
  UNKNOWN = 'UNKNOWN'

  def is_terminal(self) -> bool:
    '''tests if job status is terminal

    If the status is terminal, then the assumption is that it will not change
    again, so we will not query the compute backend any further for job status.
    '''
    return self.name in ['SUCCEEDED', 'FAILED', 'STOPPED', 'UNKNOWN']


# ----------------------------------------------------------------------------
class Platform(str, Enum):
  '''execution platforms'''
  CAIP = 'CAIP'
  GKE = 'GKE'
  LOCAL = 'LOCAL'
  TEST = 'TEST'


# ----------------------------------------------------------------------------
# we are using the sqlalchemy declarative syntax
Base = declarative_base()


# ----------------------------------------------------------------------------
def init_db(engine: Engine):
  '''initializes the database to create all of the tables defined by the
  orm objects declared here if they do not already exist.
  '''
  Base.metadata.create_all(engine)


# ----------------------------------------------------------------------------
# sqlite's datetime is a bit crippled so we set times in python, rather
# than using server-side functions, see:
# docs.sqlalchemy.org/en/13/core/type_basics.html#sqlalchemy.types.DateTime


def sorted_dict(d: Dict[str, Any]) -> OrderedDict:
  '''shorthand for generating a key-ordered dict'''
  if d is None:
    return OrderedDict()
  return OrderedDict((k, d[k]) for k in sorted(d.keys()))


# ----------------------------------------------------------------------------
class ContainerSpec(Base):
  '''caliban container spec

  This class contains the information specifying how to generate a docker
  container for use in caliban.

  Please do not instantiate this class directly via its constructor.
  Instead, use the ContainerSpec.get_or_create() method, or query the database
  using a session.query() call. The get_or_create() method returns an existing
  container spec if a matching instance already exists in the database, or
  creates a new instance otherwise.

  Properties:
  id (int): unique identifier, populated by backend database
  user (str): user who created this instance
  spec (JSON): json dictionary containing the docker creation parameters
  created (datetime): timestamp of creation time of this instance
  experiments (iterable of Experiment instances): Experiment instances based on
              this ContainerSpec
  '''
  __tablename__ = "container_specs"

  id = Column(Integer, primary_key=True)
  user = Column(String)
  spec = Column(JSON)
  created = Column(DateTime(timezone=True), nullable=False)
  experiments = relationship('Experiment',
                             back_populates='container_spec',
                             order_by='Experiment.created')

  def __init__(
      self,
      spec: Dict[str, Any],
      user: Optional[str] = None,
  ):
    '''ContainerSpec

    Args:
    spec: dictionary containing docker container creation parameters
    user: username, if None then user is automatically detected
    '''
    self.user = user or current_user()
    self.spec = sorted_dict(spec)
    self.created = datetime.now().astimezone()

  @classmethod
  def get_or_create(
      cls,
      session: Session,
      spec: Dict[str, Any],
      user: Optional[str] = None,
  ) -> "ContainerSpec":
    '''gets an existing instance, or creates a new one as necessary

    Args:
    session: a sqlalchemy session
    spec: a dictionary containing the docker creation parameters
    user: the user creating this instance, if None then user is detected

    Returns:
    a ContainerSpec instance
    '''
    new_spec = ContainerSpec(spec, user)

    existing = session.query(ContainerSpec)
    existing = existing.filter(
        ContainerSpec.user == new_spec.user,
        ContainerSpec.spec.cast(String) == json.dumps(new_spec.spec),
    )

    return existing.first() or new_spec


# ----------------------------------------------------------------------------
class ExperimentGroup(Base):
  '''caliban experiment group

  This class constitutes a group of experiments.

  Please do not instantiate this class directly via its constructor.
  Instead, use the ExperimentGroup.get_or_create() method, or query the database
  using a session.query() call. The get_or_create() method returns an existing
  experiment group if a matching instance already exists in the database, or
  creates a new instance otherwise.

  Properties:
  id (int): unique id, populated by backend database
  name (str): experiment group name
  created (datetime): creation timestamp
  user (str): user who created this experiment group
  experiments (Iterable[Experiment]): experiments associated with this group
  '''
  __tablename__ = 'experiment_groups'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  created = Column(DateTime(timezone=True), nullable=False)
  user = Column(String)

  # experiment group(one)->experiment(many)
  experiments = relationship(
      'Experiment',
      back_populates='xgroup',
      order_by='Experiment.created',
  )

  def __init__(
      self,
      name: Optional[str] = None,
      user: Optional[str] = None,
  ):
    '''ExperimentGroup

    name: name for this experiment group, if None, a name is auto-generated
    user: username, if None then user is auto-detected
    '''

    self.user = user or current_user()
    self.created = datetime.now().astimezone()
    self.name = name or self.generate_name(self.user, self.created)

  @classmethod
  def get_or_create(
      cls,
      session: Session,
      name: Optional[str] = None,
      user: Optional[str] = None,
  ) -> "ExperimentGroup":
    '''gets an existing instance, or creates a new one as necessary

    Args:
    session: a sqlalchemy database session
    name: the name of this experiment group, if None one is auto-generated
    user: username, if None then the user is auto-detected

    Returns:
    an ExperimentGroup instance
    '''
    xg = ExperimentGroup(name=name, user=user)

    existing = session.query(ExperimentGroup)
    existing = existing.filter(
        ExperimentGroup.user == xg.user,
        ExperimentGroup.name == xg.name,
    ).first()
    return existing or xg

  @classmethod
  def generate_name(
      cls,
      user: Optional[str] = None,
      date: Optional[datetime] = None,
  ) -> str:
    '''generate a default name for an experiment group'''
    user = user or current_user()
    date = date or datetime.now().astimezone()
    return (f'{user}-xgroup-{date.strftime("%Y-%m-%d-%H-%M-%S")}')

  def __repr__(self) -> str:
    return (f'<ExperimentGroup(id: {self.id} '
            f'name: {self.name} created: {self.created})>')


# ----------------------------------------------------------------------------
class Experiment(Base):
  '''caliban experiment

  This class constitutes a set of parameters used to perform an experiment
  using caliban. An Experiment is associated with a ContainerSpec and an
  ExperimentGroup. Thus an experiment describes a specific combination of
  parameters for a given ContainerSpec, which can then be used to create a
  job instance which will run on a specific compute platform like CAIP or GKE
  using a concrete instantiation of the docker container described by the
  ContainerSpec.

  Each Experiment can therefore be associated with multiple JobSpecs and
  Jobs, which are explicit executions of the experiment against a specific
  compute backend and docker container instance.

  Please do not instantiate this class directly via its constructor.
  Instead, use the Experiment.get_or_create() method, or query the database
  using a session.query() call. The get_or_create() method returns an existing
  experiment if a matching instance already exists in the database, or
  creates a new instance otherwise.

  properties:

  id (int): unique identifier
  created (datetime): creation time
  args (JSON): a list of positional args
  kwargs (JSON): a dictionary of keyword-args
  container_spec (ContainerSpec): the container spec associated with this experiment
  xgroup (ExperimentGroup): the experiment group associated with this experiment
  job_specs (Iterable[JobSpec]): job specs assocated with this experiment
  jobs (Iterable[Job]): job instances of this experiment
  '''
  __tablename__ = 'experiments'

  id = Column(Integer, primary_key=True)
  created = Column(DateTime(timezone=True), nullable=False)
  args = Column(JSON)
  kwargs = Column(JSON)

  container_spec_id = Column(Integer, ForeignKey('container_specs.id'))
  container_spec = relationship('ContainerSpec', back_populates='experiments')

  # experiment group(one)-experiment(many)
  xgroup_id = Column(Integer, ForeignKey('experiment_groups.id'))
  xgroup = relationship('ExperimentGroup', back_populates='experiments')

  job_specs = relationship('JobSpec', back_populates='experiment')
  jobs = relationship('Job',
                      back_populates='experiment',
                      order_by='Job.created')

  def __init__(
      self,
      args: Optional[List[str]] = None,
      kwargs: Optional[Dict[str, Any]] = None,
  ):
    '''Experiment

    Args:
    args: positional arguments for this experiment
    kwargs: keyword-args for this experiment
    '''
    self.args = args
    self.kwargs = sorted_dict(kwargs)
    self.created = datetime.now().astimezone()

  @classmethod
  def _existing(
      cls,
      e: "Experiment",
      xgroup: ExperimentGroup,
      container_spec: ContainerSpec,
      session: Session,
  ) -> Optional["Experiment"]:
    '''returns existing instance of given experiment, or None if none exists'''
    existing = session.query(Experiment)
    existing = existing.join(ExperimentGroup)
    existing = existing.join(ContainerSpec)

    existing = existing.filter(
        ExperimentGroup.id == xgroup.id,
        ContainerSpec.id == container_spec.id,
        xgroup.id == xgroup.id,
        Experiment.args.cast(String) == json.dumps(e.args),
        Experiment.kwargs.cast(String) == json.dumps(e.kwargs),
    )

    return existing.first()

  @classmethod
  def get_or_create(
      cls,
      xgroup: ExperimentGroup,
      container_spec: ContainerSpec,
      args: Optional[List[str]] = None,
      kwargs: Optional[Dict[str, Any]] = None,
  ) -> "Experiment":
    '''gets an existing instance, or creates a new one as necessary

    Args:
    xgroup: the experiment group for this experiment
    container_spec: this container spec for this experiment
    args: list of positional args
    kwargs: dictionary of keyword args

    Returns:
    Experiment instance
    '''

    session = object_session(xgroup)
    e = Experiment(args=args, kwargs=kwargs)

    # container_spec or xgroup have not been persisted, so this must be
    # a new experiment
    if xgroup.id is None or container_spec.id is None:
      xgroup.experiments.append(e)
      container_spec.experiments.append(e)
      return e

    # check for existing experiment
    existing = cls._existing(
        e=e,
        xgroup=xgroup,
        container_spec=container_spec,
        session=session,
    )

    if existing is not None:
      return existing

    xgroup.experiments.append(e)
    container_spec.experiments.append(e)
    return e

  def __repr__(self) -> str:
    return (f'<Experiment(id: {self.id} created: {self.created})>')


# ----------------------------------------------------------------------------
class JobSpec(Base):
  '''caliban job spec

  This class constitutes a compute-platform-specific specification for
  executing a job. This class maps an Experiment to a specific instance
  for execution, and is thus associated with an Experiment and a specific
  Platform. A job spec can have multiple job instances associated with it,
  corresponding to executions of the spec.

  Please do not instantiate this class directly via its constructor.
  Instead, use the JobSpec.get_or_create() method, or query the database
  using a session.query() call. The get_or_create() method returns an existing
  job spec if a matching instance already exists in the database, or
  creates a new instance otherwise.

  properties:

  id (int): unique id generated by database backend
  created (datetime): creation timestamp
  spec (JSON): dictionary describing job spec for given compute platform
  platform (Platform): compute platform
  experiment (Experiment): experiment for this job spec
  jobs (Iterable[Job]): job instances of this spec
  '''
  __tablename__ = 'job_specs'

  id = Column(Integer, primary_key=True)
  created = Column(DateTime(timezone=True), nullable=False)
  spec = Column(JSON, nullable=False)
  platform = Column(sqlalchemy.Enum(Platform), nullable=False)

  # Experiment(one)->JobSpec(many)
  experiment_id = Column(Integer, ForeignKey('experiments.id'))
  experiment = relationship('Experiment', back_populates='job_specs')

  # JobSpec(one)->Jobs(many)
  jobs = relationship('Job', back_populates='spec', order_by='Job.created')

  def __init__(
      self,
      spec: Dict[str, Any],
      platform: Platform,
  ):
    '''JobSpec

    spec: job specification
    platform: compute platform
    '''

    self.spec = sorted_dict(spec)
    self.platform = platform
    self.created = datetime.now().astimezone()

  @classmethod
  def _existing(
      cls,
      s: "JobSpec",
      experiment: Experiment,
      session: Session,
  ) -> Optional["JobSpec"]:
    '''returns existing JobSpec if one exists, None otherwise'''
    existing = session.query(JobSpec).join(Experiment)
    existing = existing.filter(
        JobSpec.platform == s.platform,
        JobSpec.spec.cast(String) == json.dumps(s.spec),
        Experiment.id == experiment.id,
    )
    return existing.first()

  @classmethod
  def get_or_create(
      cls,
      experiment: Experiment,
      spec: Dict[str, Any],
      platform: Platform,
  ) -> "JobSpec":
    '''gets an existing instance, or creates a new one as necessary

    Args:
    experiment: experiment for this job spec
    spec: job spec data
    platform: compute platform
    '''
    session = object_session(experiment)
    s = JobSpec(spec=spec, platform=platform)

    if experiment.id is None:
      experiment.job_specs.append(s)
      return s

    existing = cls._existing(s=s, experiment=experiment, session=session)

    if existing is not None:
      return existing

    experiment.job_specs.append(s)
    return s

  def __repr__(self):
    return (f'<JobSpec(id: {self.id} created: {self.created})>')


# ----------------------------------------------------------------------------
class Job(Base):
  '''caliban job

  This class constitutes an execution of a job on a compute platform.

  properties:
  id (int): unique id populated by database backend
  created (datetime): creation timestamp
  spec (JobSpec): spec for this job
  experiment (Experiment): experiment associated with this job
  container (str): container id
  status (JobStatus): execution status
  details (JSON): job- and platform-specific details for job
  user (str): username
  '''
  __tablename__ = 'jobs'

  id = Column(Integer, primary_key=True)
  created = Column(DateTime(timezone=True), nullable=False)

  job_spec_id = Column(Integer, ForeignKey('job_specs.id'))
  spec = relationship('JobSpec', back_populates='jobs')

  experiment_id = Column(Integer, ForeignKey('experiments.id'))
  experiment = relationship('Experiment', back_populates='jobs')

  container = Column(String, nullable=False)
  status = Column(sqlalchemy.Enum(JobStatus))
  details = Column(JSON)
  user = Column(String)

  def __init__(
      self,
      spec: JobSpec,
      container: str,
      details: Dict[str, Any],
      status: Optional[JobStatus] = JobStatus.SUBMITTED,
      user: Optional[str] = None,
  ):
    '''Job

    spec: job spec
    container: container id for this job
    details: job- and platform-specific details for job
    status: initial status for this job
    user: user who created this job, if None will be auto-detected
    '''
    self.created = datetime.now().astimezone()
    self.container = container
    self.details = sorted_dict(details)  # 'metadata' is reserved by sqlalchemy
    self.status = status
    self.user = user or current_user()

    spec.jobs.append(self)
    spec.experiment.jobs.append(self)

  def __repr__(self):
    return (f'<Job(id: {self.id} created: {self.created})>')
