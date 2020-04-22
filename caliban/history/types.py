'''types for caliban.history'''

from enum import Enum
from caliban.gke.types import JobStatus as GkeStatus
from caliban.cloud.types import JobStatus as CloudStatus
from typing import Union, NamedTuple, Dict, Any


# ----------------------------------------------------------------------------
class TestJobStatus(Enum):
  '''null compute backend job status, for testing'''
  SUBMITTED = 0
  RUNNING = 1
  SUCCEEDED = 2
  FAILED = 3

  def is_terminal(self) -> bool:
    return self.name in ['SUCCEEDED', 'FAILED']


# ----------------------------------------------------------------------------
# todo: relocate this to the right place, modify appropriately
class LocalJobStatus(Enum):
  '''local compute backend job status'''
  SUBMITTED = 0
  RUNNING = 1
  SUCCEEDED = 2
  FAILED = 3

  def is_terminal(self) -> bool:
    return self.name in ['SUCCEEDED', 'FAILED']


# ----------------------------------------------------------------------------
JobStatus = Union[GkeStatus, CloudStatus, LocalJobStatus, TestJobStatus]


# ----------------------------------------------------------------------------
class Platform(Enum):
  '''execution platforms'''
  CAIP = 'Cloud AI Platform'
  GKE = 'Google Kubernetes Engine'
  LOCAL = 'Local'
  TEST = 'Testing Platform'


# ----------------------------------------------------------------------------
class SubmissionStatus(NamedTuple):
  '''status for job submission to compute backend

  The spec contained here is a complete specification that the given
  backend can use to create and execute a new run.

  spec: dictionary describing job submission spec
  status: initial status for job run
  '''
  spec: Dict[str, Any]
  status: JobStatus
