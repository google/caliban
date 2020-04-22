'''caliban history null storage'''

import uuid

from typing import Optional, List, Tuple, Dict, Any, Iterable, Union
from caliban.history.interfaces import (Storage, Experiment, Job, Run,
                                        Collection, ComputePlatform)

from caliban.history.experiment import ExperimentBase
from caliban.history.job import JobBase
from caliban.history.run import RunBase
import caliban.config as conf
from copy import deepcopy


# ----------------------------------------------------------------------------
def create_null_storage() -> Storage:
  return _NullStorage()


# ----------------------------------------------------------------------------
class _NullRun(RunBase):
  '''null-storage run'''

  def __init__(self, job: Job, d: Dict[str, Any]):
    super().__init__(d)
    self._null_job = job

  def job(self) -> Job:
    return self._null_job

  def clone(self) -> Optional[Run]:
    new_run = deepcopy(self)
    self._null_job._runs.append(new_run)
    return new_run


# ----------------------------------------------------------------------------
class _NullJob(JobBase):
  '''null-storage job'''

  def __init__(self, experiment: Experiment, d: Dict[str, Any]):
    super().__init__(d)
    self._exp = experiment
    self._runs = []

  def runs(self) -> Iterable[Run]:
    '''returns job runs'''
    return self._runs

  def experiment(self) -> Experiment:
    '''returns the parent experiment of this job'''
    return self._exp

  def submit(self, compute: ComputePlatform) -> Optional[Run]:
    sub = compute.submit(self)
    if sub is None:
      return None

    d = RunBase.create_dict(job=self.id(),
                            platform=compute.platform(),
                            status=sub.status,
                            spec=sub.spec)
    self._runs.append(_NullRun(job=self, d=d))

    return self._runs[-1]


# ----------------------------------------------------------------------------
class _NullExperiment(ExperimentBase):
  '''null-storage experiment'''

  def __init__(
      self,
      storage: Storage,
      d: Dict[str, Any],
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
  ):
    super().__init__(d)
    self._storage = storage
    self._jobs = self._create_jobs(configs=configs, args=args)

  def jobs(self) -> Iterable[Job]:
    '''returns jobs associated with this experiment'''
    return self._jobs

  def _create_jobs(
      self,
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
  ) -> List[Job]:

    dicts = JobBase.create_dicts(
        name=self.name(),
        user=self.user(),
        configs=configs,
        args=args,
        experiment=self.id(),
    )
    return [_NullJob(experiment=self, d=d) for d in dicts]


# ----------------------------------------------------------------------------
class _NullStorage(Storage):
  '''simple null storage'''

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
    command: command if not None, container default otherwise
    configs: list of job configurations
    args: list of common arguments for every job
    user: user creating this experiment, if None uses current user

    Returns:
    Experiment instance on success, None otherwise
    '''

    return _NullExperiment(
        storage=self,
        d=ExperimentBase.create_dict(
            name=name,
            container=container,
            command=command,
            user=user,
        ),
        configs=configs,
        args=args,
    )

  def collection(self, name: str) -> Optional[Collection]:
    '''gets given collection'''
    return None
