import os
from typing import Optional
from contextlib import contextmanager
from typing import Dict, Any
import logging
from copy import deepcopy

from googleapiclient import discovery

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, Session

from caliban.history.types import Job, JobStatus, init_db, Platform, JobSpec
from caliban.gke.cluster import Cluster
from caliban.gke.utils import default_credentials
from caliban.gke.types import JobStatus as GkeStatus
from caliban.cloud.types import JobStatus as CloudStatus

DB_URL_ENV = 'CALIBAN_DB_URL'
MEMORY_DB_URL = 'sqlite:///:memory:'
DEFAULT_DB_URL = 'sqlite:///:memory:'

# todo: change default db path once feature is enabled
#'sqlite:///~/.caliban/caliban.db'


# ----------------------------------------------------------------------------
def _create_sqa_engine(
    url: str = DEFAULT_DB_URL,
    echo: bool = False,
) -> Engine:
  '''creates a sqlalchemy Engine instance

  Args:
  url: url of database
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''

  # this is a local sqlite db
  if url.startswith('sqlite:///') and url != 'sqlite:///:memory:':
    path, db = os.path.split(url.replace('sqlite:///', ''))
    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    full_path = os.path.join(path, db)
    url = f'sqlite:///{full_path}'

  engine = create_engine(url, echo=echo)
  init_db(engine)
  return engine


# ----------------------------------------------------------------------------
def get_sql_engine(
    url: Optional[str] = None,
    echo: bool = False,
) -> Engine:
  '''gets a sqlalchemy Engine instance

  Args:
  url: url of database, if None, uses DB_URL_ENV environment variable or
       DEFAULT_DB_URL as fallbacks, in that order
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  if url is not None:
    return _create_sqa_engine(url=url, echo=echo)
  return _create_sqa_engine(
      url=(os.environ.get(DB_URL_ENV) or DEFAULT_DB_URL),
      echo=echo,
  )


# ----------------------------------------------------------------------------
def get_mem_engine(echo: bool = False) -> Engine:
  '''gets a sqlalchemy engine connection to an in-memory sqlite instance

  Args:
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  return _create_sqa_engine(url=MEMORY_DB_URL)


# ----------------------------------------------------------------------------
@contextmanager
def session_scope(engine: Engine) -> Session:
  '''returns a sqlalchemy session using the provided engine

  This contextmanager commits all pending session changes on scope exit,
  and on an exception rolls back pending changes. The returned session is
  closed on final scope exit.

  Args:
  engine: sqlalchemy engine

  Returns:
  Session
  '''
  session = sessionmaker(bind=engine)()
  try:
    yield session
    session.commit()
  except:
    session.rollback()
    raise
  finally:
    session.close()
