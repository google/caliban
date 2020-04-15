'''run base'''

import uuid

from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union

from caliban.history.interfaces import Run, Platform


# ----------------------------------------------------------------------------
class RunBase(Run):
  '''(abstract) base for Run

  provides:
    DictSerializable, Timestamped, Id, Named, User, PlatformSpecific

  does not provide:
    status(), request(), job()
  '''

  def __init__(self, d: Dict[str, Any]):
    self._id = d['id']
    self._timestamp = d['timestamp']
    self._name = d['name']
    self._job = d['job']
    self._user = d['user']
    self._platform = d['platform']

  def to_dict(self) -> Dict[str, Any]:
    '''serializes object to dictionary'''
    return self.create_dict(
        id=self._id,
        user=self._user,
        name=self._name,
        timestamp=self._timestamp,
        job=self._job,
    )

  def timestamp(self) -> datetime:
    return self._timestamp

  def user(self) -> str:
    return self._user

  def id(self) -> str:
    return self._id

  def name(self) -> str:
    return self._name

  def platform(self) -> Platform:
    return Platform[self._platform]

  @classmethod
  def create_dict(cls, id: str, name: str, user: str, timestamp: datetime,
                  job: str, platform: Platform) -> Dict[str, str]:
    '''creates a RunBase dictionary'''
    return {
        'id': id,
        'name': name,
        'user': user,
        'timestamp': timestamp,
        'job': job,
        'platform': platform.name,
    }
