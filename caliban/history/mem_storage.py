'''caliban history mem storage'''

import uuid
import operator
import itertools
import pprint as pp
from copy import deepcopy

from typing import (Optional, List, Tuple, Dict, Any, Iterable, Union, TypeVar,
                    Type, Callable, NamedTuple)
from caliban.history.interfaces import (Storage, Experiment, Job, Run,
                                        Collection, QueryOp, HistoryObject,
                                        Query)
from caliban.history.experiment import ExperimentBase
from caliban.history.run import RunBase
from caliban.history.job import JobBase, StorageJob
from caliban.history.clause import Clause
import caliban.config as conf

_MemStorageType = TypeVar('_MemStorageType', bound='_MemStorage')
_MemCollectionType = TypeVar('_MemCollectionType', bound='_MemCollection')


# ----------------------------------------------------------------------------
class _MemQuery(Query):
  '''memory-store query'''

  def __init__(
      self,
      collection: _MemCollectionType,
      field: str,
      op: QueryOp,
      value: Any,
  ):
    self._collection = collection
    self._order_by = None
    self._order_by_dir = Query.Direction.ASCENDING
    self._limit = None
    self._clauses = [Clause(field, op, value)]

  def copy(self) -> "_MemQuery":
    return deepcopy(self)

  def execute(self) -> Optional[Iterable[HistoryObject]]:
    return self._collection._execute_query(self)

  def order_by(self, field: str, direction: Query.Direction) -> Query:
    q = self.copy()
    q._order_by = field
    q._order_by_dir = direction
    assert False, 'not implemented yet'
    return q

  def limit(self, count: int) -> Query:
    q = self.copy()
    q._limit = count
    return q

  def where(self, field: str, op: QueryOp, value: Any) -> Query:
    q = self.copy()
    q._clauses.append(Clause(field, op, value))
    return q

  def __str__(self):
    return ' AND '.join(map(lambda c: str(c),
                            self._clauses)) + ' LIMIT {}'.format(self._limit)


# ----------------------------------------------------------------------------
class _MemRun(RunBase):
  '''memory-store run'''

  def __init__(
      self,
      storage: _MemStorageType,
      d: Dict[str, Any],
      create=False,
  ):
    super().__init__(d)
    self._storage = storage
    # todo: implement fully


# ----------------------------------------------------------------------------
class _MemExperiment(ExperimentBase):
  '''mem-store experiment'''

  def __init__(
      self,
      storage: _MemStorageType,
      d: Dict[str, Any],
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
      create: bool = False,
  ):
    super().__init__(d)
    self._storage = storage

    if not create:
      return

    self._storage._store['experiments']._add(self)

    for j in self._create_jobs(configs=configs, args=args):
      self._storage._store['jobs']._add(j)

  def jobs(self) -> Iterable[Job]:
    return self._storage.collection('jobs').where('experiment', QueryOp.EQ,
                                                  self.id()).execute()

  def _create_jobs(
      self,
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
  ) -> List[Job]:

    dicts = JobBase.create_dicts(
        name=self.name(),
        user=self.user(),
        experiment=self.id(),
        configs=configs,
        args=args,
    )
    return [StorageJob(storage=self._storage, d=d, create=True) for d in dicts]


# ----------------------------------------------------------------------------
class _MemCollection(Collection):
  '''simple memory collection'''

  def __init__(self, constructor: Callable[[Dict[str, Any]],
                                           Optional[HistoryObject]]):
    self._d = {}
    self._constructor = constructor

  def get(self, id: str) -> Optional[HistoryObject]:
    d = self._d.get(id)
    return self._constructor(d) if d is not None else None

  def where(self, field: str, op: QueryOp, value: Any) -> Query:
    return _MemQuery(collection=self, field=field, op=op, value=value)

  def _add(self, obj: HistoryObject):
    self._d[obj.id()] = obj.to_dict()

  def _execute_query(self, q: _MemQuery) -> Optional[Iterable[HistoryObject]]:
    return map(
        self._constructor,
        itertools.islice(
            filter(lambda x: all(c(x) for c in q._clauses), self._d.values()),
            q._limit))


# ----------------------------------------------------------------------------
class _MemStorage(Storage):
  '''simple memory-backed storage'''

  def __init__(self):
    self._store = {
        'experiments':
            _MemCollection(constructor=lambda d: _MemExperiment(
                storage=self, d=d, create=False)),
        'jobs':
            _MemCollection(constructor=lambda d: StorageJob(
                storage=self, d=d, create=False)),
        'runs':
            _MemCollection(
                constructor=lambda d: _MemRun(storage=self, d=d, create=False)),
    }

  def create_experiment(
      self,
      name: str,
      container: str,
      command: Optional[str],
      configs: Optional[List[conf.Experiment]] = None,
      args: Optional[List[str]] = None,
      user: Optional[str] = None,
  ) -> Optional[Experiment]:

    return _MemExperiment(
        storage=self,
        d=ExperimentBase.create_dict(
            name=name,
            container=container,
            command=command,
            user=user,
        ),
        configs=configs,
        args=args,
        create=True,
    )

  def collection(self, name: str) -> Optional[Collection]:
    return self._store.get(name)


# ----------------------------------------------------------------------------
def create_mem_storage() -> Storage:
  return _MemStorage()
