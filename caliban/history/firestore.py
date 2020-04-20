'''firestore-backed store'''

import uuid

from functools import reduce
from copy import deepcopy
import itertools

from typing import (Optional, List, Tuple, Dict, Any, Iterable, Union, TypeVar,
                    Type, Callable, NamedTuple)

from google.auth.credentials import Credentials
from google.cloud import firestore
from google.cloud.firestore import (CollectionReference, DocumentSnapshot)

from caliban.history.types import Platform, JobStatus
from caliban.history.interfaces import (Experiment, Job, Run, Storage,
                                        ComputePlatform, Collection,
                                        HistoryObject, Query, QueryOp)
from caliban.history.experiment import ExperimentBase
from caliban.history.run import RunBase
from caliban.history.job import JobBase, StorageJob
from caliban.history.clause import Clause

import caliban.config as conf

_FirestoreStorageType = TypeVar('_FirestoreStorageType',
                                bound='_FirestoreStorage')

_FirestoreCollectionType = TypeVar('_FirestoreCollectionType',
                                   bound='_FirestoreCollection')

_FirestoreQueryType = TypeVar('_FirestoreQueryType', bound='_FirestoreQuery')


# ----------------------------------------------------------------------------
def create_firestore_storage(project_id: str,
                             creds: Credentials) -> Optional[Storage]:
  '''create/access a firestore-backed store'''
  db = firestore.Client(project=project_id, credentials=creds)
  return _FirestoreStorage(db, creds)


# ----------------------------------------------------------------------------
class _FirestoreQuery(Query):
  '''firestore query

  This is an implementation of the caliban.history.Query interface for
  firestore-based storage backends. The interface definition contains
  additional documentation for this type.

  This implementation keeps a reference to its firestore-backed collection
  for execution.
  '''

  def __init__(
      self,
      collection: _FirestoreCollectionType,
      field: str,
      op: QueryOp,
      value: Any,
  ):
    self._collection = collection
    self._order_by = None
    self._order_by_dir = Query.Direction.ASCENDING
    self._limit = None
    self._clauses = [Clause(field, op, value)]

  def copy(self) -> _FirestoreQueryType:
    '''creates a deep copy of this instance'''
    c0 = self._clauses[0]
    q = _FirestoreQuery(self._collection, c0.field, c0.op, c0.value)
    q._clauses = deepcopy(self._clauses)
    return q

  def execute(self) -> Optional[Iterable[HistoryObject]]:
    return self._collection._execute_query(self)

  def order_by(self, field: str, direction: Query.Direction) -> Query:
    q = self.copy()
    q._order_by = field
    q._order_by_dir = direction
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
class _FirestoreRun(RunBase):
  '''A firestore-backed caliban.history.Run implementation.

  Please see caliban.history.Run for additional documentation on this
  type.

  This is incomplete at the moment, but is needed for testing the rest
  of the interface types.
  '''

  def __init__(
      self,
      storage: _FirestoreStorageType,
      d: Dict[str, Any],
      create=False,
  ):
    super().__init__(d)
    self._storage = storage
    # todo: implement fully


# ----------------------------------------------------------------------------
class _FirestoreExperiment(ExperimentBase):
  '''A firestore-backed caliban.history.Experiment implementation.

  Please see the interface definition for additional documentation on this
  type.

  This implementation keeps a reference to its backing Storage implementation
  for retrieving assocated jobs.

  Args:
  storage: backing firestore-based store
  d: dictionary representation of the experiment
  configs: parameter configs for the experiment
  args: arguments for the experiment
  create: True if the experiment should be created and persisted in the store,
          False if the experiment should be pulled from the store
  '''

  def __init__(
      self,
      storage: _FirestoreStorageType,
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
    '''this is private method that creates jobs for this experiment and
    returns them in a list.
    '''
    dicts = JobBase.create_dicts(
        name=self.name(),
        user=self.user(),
        experiment=self.id(),
        configs=configs,
        args=args,
    )

    return [StorageJob(storage=self._storage, d=d, create=True) for d in dicts]


# ----------------------------------------------------------------------------
class _FirestoreCollection(Collection):
  '''firestore-backed implementation of caliban.history.Collection.

  Please see the interface type for additional documentation on this type.
  This is similar to firestore collections:
  https://firebase.google.com/docs/firestore/data-model#collections

  Args:

  name: the name of this collection
  storage: firestore-based backing store for this collection
  constructor: a callable to convert stored dictionaries to the associated
               class for this store.
  '''

  _ORDER_BY_DIR = {
      Query.Direction.ASCENDING: firestore.Query.ASCENDING,
      Query.Direction.DESCENDING: firestore.Query.DESCENDING
  }

  def __init__(
      self,
      name: str,
      storage: _FirestoreStorageType,
      constructor: Callable[[Dict[str, Any]], Optional[HistoryObject]],
  ):
    self._name = name
    self._storage = storage
    self._constructor = constructor
    self._c = self._storage._db.collection(self._name)

  def get(self, id: str) -> Optional[HistoryObject]:
    d = self._c.document(id).get()
    return self._constructor(d.to_dict()) if d.exists else None

  def where(self, field: str, op: QueryOp, value: Any) -> Query:
    return _FirestoreQuery(collection=self, field=field, op=op, value=value)

  def _add(self, obj: HistoryObject):
    '''add the provided object to the store'''
    self._c.document(obj.id()).create(obj.to_dict())

  def _execute_single_clause_query(
      self,
      c: Clause,
      order_by: Optional[str],
      order_by_dir: Optional[Query.Direction],
      limit: Optional[int],
  ) -> Optional[Iterable[Dict[str, Any]]]:
    '''
    This class-private method executes a single-clause query on the
    remote Firestore instance.

    Firestore requires an index for all queries in order to maintain
    performance, and automatically creates them for simple queries.
    For more complicated, combined queries, you must manually create
    an index, which is problematic for this use case. As a result, we
    use this internal method to execute a single-clause query against
    the remote firestore instance, and then process the remaining clauses
    locally.

    See: https://firebase.google.com/docs/firestore/query-data/index-overview

    Args:
    c: the single Clause for this query
    order_by: field to use for ordering the results
    order_by_dir: direction for ordering
    limit: maximum number of results to return.

    Returns:
    iterable of dictionary-representations for results on success, None
      otherwise
    '''
    fq = self._c.where(c.field, c.op.value, c.value)

    if order_by is not None:
      fq = fq.order_by(order_by, self._ORDER_BY_DIR[order_by_dir])

    if limit is not None:
      fq = fq.limit(limit)

    return map(lambda x: x.to_dict(), fq.stream())

  def _execute_query(
      self,
      q: _FirestoreQuery,
  ) -> Optional[Iterable[HistoryObject]]:
    '''executes a query on the collection

    Args:
    q: the Query to execute

    Returns:
    iterable of objects matching the query on success, None on error
    '''
    opt = lambda x: x if len(q._clauses) == 1 else None

    # firestore automatically sets up single-field query indices
    # so we run first clause against firestore db
    docs = self._execute_single_clause_query(
        c=q._clauses[0],
        order_by=opt(q._order_by),
        order_by_dir=opt(q._order_by_dir),
        limit=opt(q._limit),
    )

    if len(q._clauses) > 1:
      docs = itertools.islice(
          filter(lambda x: all(c(x) for c in q._clauses[1:]), docs), q._limit)

    return map(lambda x: self._constructor(x), docs)


# ----------------------------------------------------------------------------
class _FirestoreStorage(Storage):
  '''firestore-backed caliban.history.Storage implementation

  Please see the interface type for additional documentation for this class.

  Args:
  db: a firestore client for interacting with the backing store
  creds: credentials for interacting with the storage backend and compute backends
  '''

  def __init__(self, db: firestore.Client, creds: Credentials):
    self._db = db
    self._creds = creds
    self._store = {
        'experiments':
            _FirestoreCollection(name='experiments',
                                 storage=self,
                                 constructor=lambda d: _FirestoreExperiment(
                                     storage=self, d=d, create=False)),
        'jobs':
            _FirestoreCollection(name='jobs',
                                 storage=self,
                                 constructor=lambda d: StorageJob(
                                     storage=self, d=d, create=False)),
        'runs':
            _FirestoreCollection(name='runs',
                                 storage=self,
                                 constructor=lambda d: _FirestoreRun(
                                     storage=self, d=d, create=False)),
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

    return _FirestoreExperiment(
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
