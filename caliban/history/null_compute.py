'''null compute backend for testing'''

import random
from enum import Enum
from typing import Dict, Any, TypeVar, Optional

from caliban.history.types import Platform, TestJobStatus, SubmissionStatus
from caliban.history.interfaces import ComputePlatform, Job, Run


# ----------------------------------------------------------------------------
def get_status(r: Run) -> TestJobStatus:
  '''gets status for null compute run

  Just returns a random status, which will eventually result in a terminal
  state. At that point, the final status will be persisted and queries
  will stop to the backend. This is of course just for testing.
  '''
  return random.choice([x for x in TestJobStatus])


# ----------------------------------------------------------------------------
class _NullCompute(ComputePlatform):
  '''null compute platform for testing'''

  def __init__(self):
    self._platform = Platform.TEST

  def name(self) -> str:
    return self._platform.name

  def platform(self) -> Platform:
    return self._platform

  def submit(self, job: Job) -> Optional[SubmissionStatus]:
    return SubmissionStatus(spec={}, status=TestJobStatus.SUBMITTED)


# ----------------------------------------------------------------------------
def create_null_compute() -> ComputePlatform:
  return _NullCompute()
