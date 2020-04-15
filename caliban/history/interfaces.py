'''caliban history interfaces'''

import abc
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union
from enum import Enum
from datetime import datetime

from caliban.history.types import Platform, JobStatus
import caliban.config as conf


# ----------------------------------------------------------------------------
class DictSerializable(abc.ABC):
  '''interface for classes that are dictionary-serializable'''

  @abc.abstractmethod
  def to_dict(self) -> Dict[str, Any]:
    '''serializes object to dictionary'''


# ----------------------------------------------------------------------------
class Timestamped(abc.ABC):
  '''interface for timestamped classes'''

  @abc.abstractmethod
  def timestamp(self) -> datetime:
    '''returns timestamp that object was created'''


# ----------------------------------------------------------------------------
class Id(abc.ABC):
  '''interface for classes with an id'''

  @abc.abstractmethod
  def id(self) -> str:
    '''returns object id'''


# ----------------------------------------------------------------------------
class PlatformSpecific(abc.ABC):
  '''interface for classes that have platform dependence'''

  @abc.abstractmethod
  def platform(self) -> Platform:
    '''returns the compute platform for this object'''


# ----------------------------------------------------------------------------
class Named(abc.ABC):
  '''interface for classes with name'''

  @abc.abstractmethod
  def name(self) -> str:
    '''returns the name of this object'''


# ----------------------------------------------------------------------------
class User(abc.ABC):
  '''interface for classes with user'''

  @abc.abstractmethod
  def user(self) -> str:
    '''returns user that created this object'''


# ----------------------------------------------------------------------------
class Run(DictSerializable, Timestamped, Id, PlatformSpecific, Named, User):
  '''interface for caliban job run data

  A run is a single execution of a job on a specific compute platform.
  '''

  @abc.abstractmethod
  def status(self) -> JobStatus:
    '''returns the run status'''

  @abc.abstractmethod
  def request(self) -> str:
    '''returns a string representing the run request'''

  @abc.abstractmethod
  def job(self) -> "Job":
    '''returns job for this run'''


# ----------------------------------------------------------------------------
class Job(DictSerializable, Timestamped, Id, Named, User):
  '''interface for caliban job data

  A job is a single configuration of parameters for a single command.
  A job is compute-platform *independent*.
  '''

  @abc.abstractmethod
  def args(self) -> List[str]:
    '''returns command positional args'''

  @abc.abstractmethod
  def kwargs(self) -> Dict[str, str]:
    '''returns command keyword args'''

  @abc.abstractmethod
  def runs(self) -> Iterable[Run]:
    '''returns job runs'''

  @abc.abstractmethod
  def experiment(self) -> "Experiment":
    '''returns the parent experiment of this job'''


# ----------------------------------------------------------------------------
class Experiment(DictSerializable, Timestamped, Id, Named, User):
  '''interface for caliban experiment

  An experiment is a container instance and collection of jobs, and is
  compute-platform *independent*.
  '''

  @abc.abstractmethod
  def container(self) -> str:
    '''returns container identifier for this experiment'''

  @abc.abstractmethod
  def jobs(self) -> Iterable[Job]:
    '''returns jobs associated with this experiment'''

  @abc.abstractmethod
  def command(self) -> Optional[str]:
    '''returns command, or None for default container entrypoint'''


# ----------------------------------------------------------------------------
# union of all history objects
HistoryObject = Union[Experiment, Job, Run]


# ----------------------------------------------------------------------------
class QueryOp(Enum):
  '''supported operations for queries'''
  LT = '<'
  LE = '<='
  GT = '>'
  GE = '>='
  EQ = '=='
  IN = 'in'


# ----------------------------------------------------------------------------
class Queryable(abc.ABC):
  '''interface for queryable objects'''

  @abc.abstractmethod
  def where(self, field: str, op: QueryOp, value: Any) -> "Query":
    '''where query

    This is a basic 'where' query along the lines of:
    jobs.where('timestamp', QueryOp.GT, datetime(2020, 3, 27))

    Args:
    field: dot-separated field path ({'foo': {'bar': {'baz': 7}}} = foo.bar.baz)
    op: query operator
    value: query value
    '''


# ----------------------------------------------------------------------------
class Query(Queryable):
  '''query interface'''

  class Direction(Enum):
    '''ascending/descending'''
    ASCENDING = 'ASCENDING'
    DESCENDING = 'DESCENDING'

  @abc.abstractmethod
  def execute(self) -> Optional[Iterable[HistoryObject]]:
    '''executes query'''

  @abc.abstractmethod
  def order_by(self, field: str, direction: Direction) -> "Query":
    '''sets order of results

    Args:
    field: dot-separated field string
    direction: ascending/descending

    Returns:
    Query
    '''

  @abc.abstractmethod
  def limit(self, count: int) -> "Query":
    '''limits the number of results'''


# ----------------------------------------------------------------------------
class Collection(Queryable):
  '''collection interface for storage types'''

  @abc.abstractmethod
  def get(self, id: str) -> Optional[HistoryObject]:
    '''get object by id'''


# ----------------------------------------------------------------------------
class Storage(abc.ABC):
  '''history storage

  This interface specifies the methods any storage backend will provide
  for storing caliban experiments. Any storage backend will need to provide
  a method for creating an experiment, and a method for accessing collections
  in the store.

  There are three types stored are Experiments, Jobs, and Runs. Each of these
  types has more documentation on their use and scope, but the basic concept
  is that we will store metadata from caliban submissions in such a way that
  a user can review past submissions, query the status of submitted jobs, and
  perform queries on past submissions, filtering on useful fields such as
  arguments and dates.
  '''

  @abc.abstractmethod
  def create_experiment(
      self,
      name: str,
      container: str,
      command: Optional[str],
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
      user: Optional[str] = None,
  ) -> Optional[Experiment]:
    '''creates a new experiment in the store

    Args:
    name: experiment name
    container: container id
    command: command to execute, None = container default
    configs: list of job configurations
    args: list of common arguments for every job
    user: user creating this experiment, if None uses current user

    Returns:
    Experiment instance on success, None otherwise
    '''

  @abc.abstractmethod
  def collection(self, name: str) -> Optional[Collection]:
    '''gets given collection'''


# ----------------------------------------------------------------------------
class ComputePlatform(Named, PlatformSpecific):
  '''compute platform'''

  @abc.abstractmethod
  def submit(self, job: Job) -> Optional[Run]:
    '''submits a job to the compute platform

    Args:
    job: job to submit

    Returns:
    run on success, None otherwise
    '''
