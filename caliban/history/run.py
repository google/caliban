'''run base'''

import uuid

from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union

from caliban.gke.types import JobStatus as GkeStatus
from caliban.cloud.types import JobStatus as CloudStatus
from caliban.history.interfaces import Run
from caliban.history.types import (JobStatus, Platform, LocalJobStatus,
                                   TestJobStatus)
from caliban.history.status import get_run_status
import caliban.util


# ----------------------------------------------------------------------------
class RunBase(Run):
  '''(abstract) base for Run

  provides:
    DictSerializable, Timestamped, Id, Named, User, PlatformSpecific

  does not provide:
    job()
  '''

  def __init__(self, d: Dict[str, Any]):
    self._id = d['id']
    self._timestamp = d['timestamp']
    self._job = d['job']
    self._user = d['user']
    self._platform = d['platform']
    self._spec = d['spec']
    self._status = d['status']

  def to_dict(self) -> Dict[str, Any]:
    '''serializes object to dictionary'''
    return {
        'id': self._id,
        'timestamp': self._timestamp,
        'job': self._job,
        'user': self._user,
        'platform': self._platform,
        'spec': self._spec,
        'status': self._status,
    }

  def timestamp(self) -> datetime:
    return self._timestamp

  def user(self) -> str:
    return self._user

  def id(self) -> str:
    return self._id

  def platform(self) -> Platform:
    return Platform[self._platform]

  def spec(self) -> Dict[str, Any]:
    return self._spec

  @classmethod
  def create_dict(
      cls,
      job: str,
      platform: Platform,
      status: JobStatus,
      spec: Dict[str, Any],
      user: Optional[str] = None,
  ) -> Dict[str, Any]:
    '''creates a RunBase dictionary'''
    return {
        'id': uuid.uuid1().hex,
        'user': user or caliban.util.current_user(),
        'timestamp': datetime.now().astimezone(),
        'job': job,
        'platform': platform.name,
        'spec': spec,
        'status': status.name,
    }

  def typed_status(self) -> JobStatus:
    '''use our platform type to convert our string status
    into a specific enum type'''
    _TYPES = {
        Platform.CAIP: CloudStatus,
        Platform.GKE: GkeStatus,
        Platform.LOCAL: LocalJobStatus,
        Platform.TEST: TestJobStatus,
    }

    assert self.platform() in _TYPES, 'unsupported platform'
    return _TYPES[self.platform()][self._status]

  def status(self) -> JobStatus:
    if self.typed_status().is_terminal():
      return self._status
    return get_run_status(self)
