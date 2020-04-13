'''experiment base'''

import uuid
from dateutil.tz import tzlocal
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Iterable, Union
from caliban.history.types import Platform, JobStatus
from caliban.history.interfaces import Experiment, Job, Run, Storage, ComputePlatform
import caliban.util


# ----------------------------------------------------------------------------
class ExperimentBase(Experiment):
  '''(abstract) base for Experiment

  provides:
    DictSerializable, Timestamped, Id, Named, User implementations
    container() implementation

  does not provide:
    jobs()
  '''

  def __init__(
      self,
      d: Dict[str, Any],
  ):
    self._id = d['id']
    self._name = d['name']
    self._user = d['user']
    self._container = d['container']
    self._command = d['command']
    self._timestamp = d['timestamp']

  def to_dict(self) -> Dict[str, Any]:
    '''serializes object to dictionary'''
    return {
        'id': self._id,
        'user': self._user,
        'name': self._name,
        'container': self._container,
        'command': self._command,
        'timestamp': self._timestamp,
    }

  def timestamp(self) -> datetime:
    '''returns timestamp that object was created'''
    return self._timestamp

  def user(self) -> str:
    '''returns user that created this object'''
    return self._user

  def id(self) -> str:
    '''returns object id'''
    return self._id

  def container(self) -> str:
    '''returns container identifier for this experiment'''
    return self._container

  def command(self) -> Optional[str]:
    '''returns command, or None for default container entrypoint'''
    return self._command

  def name(self) -> str:
    '''returns the name of this object'''
    return self._name

  @classmethod
  def create_dict(
      cls,
      name: str,
      container: str,
      command: Optional[str] = None,
      user: Optional[str] = None,
  ) -> Dict[str, Any]:
    '''create an ExperimentBase dictionary'''
    return {
        'id': uuid.uuid1().hex,
        'user': user or caliban.util.current_user(),
        'name': name,
        'container': container,
        'command': command,
        'timestamp': datetime.now(tz=tzlocal())
    }
