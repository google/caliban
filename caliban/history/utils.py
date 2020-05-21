import os
import sys
from contextlib import contextmanager
from typing import Optional

from absl import logging
from blessings import Terminal
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from caliban.history.types import init_db

DB_URL_ENV = 'CALIBAN_DB_URL'
MEMORY_DB_URL = 'sqlite:///:memory:'
SQLITE_FILE_DB_URL = 'sqlite:///~/.caliban/caliban.db'

t = Terminal()


# ----------------------------------------------------------------------------
def _create_sqa_engine(
    url: str = SQLITE_FILE_DB_URL,
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
def get_mem_engine(echo: bool = False) -> Engine:
  '''gets a sqlalchemy engine connection to an in-memory sqlite instance

  Args:
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  return _create_sqa_engine(url=MEMORY_DB_URL, echo=echo)


# ----------------------------------------------------------------------------
def get_sql_engine(
    url: Optional[str] = None,
    strict=False,
    echo: bool = False,
) -> Engine:
  '''gets a sqlalchemy Engine instance

  Args:
  url: url of database, if None, uses DB_URL_ENV environment variable or
       SQLITE_FILE_DB_URL as fallbacks, in that order
  strict: if True, won't attempt to fall back to local or memory engines.
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  if url is None:
    url = os.environ.get(DB_URL_ENV) or SQLITE_FILE_DB_URL

  try:
    return _create_sqa_engine(url=url, echo=echo)

  except (OperationalError, OSError) as e:
    logging.error("")
    logging.error(
        t.red(
            f"Caliban failed to connect to its experiment tracking database! Details:"
        ))
    logging.error("")
    logging.error(t.red(str(e)))
    logging.error(t.red(f"Caliban attempted to connect to '{url}'."))
    logging.error(t.red(f"Try setting a different URL using ${DB_URL_ENV}."))
    logging.error("")

    if strict:
      sys.exit(1)

    else:
      # For now, we allow two levels of fallback. The goal is to make sure that
      # the job can proceed, no matter what.
      #
      # If you specify a custom URL, Caliban will fall back to the local
      # default database location. If that fails, Caliban will attempt once
      # more using an in-memory instance of SQLite. The only reason that should
      # fail is if your system doesn't support SQLite at all.

      if url == SQLITE_FILE_DB_URL:
        logging.warning(
            t.yellow(f"Attempting to proceed with in-memory database."))

        # TODO when we add our strict flag, bail here and don't even allow
        # in-memory.
        logging.warning(
            t.yellow(
                f"WARNING! This means that your job's history won't be accessible "
                f"via any of the `caliban history` commands. Proceed at your future self's peril."
            ))
        return get_sql_engine(url=MEMORY_DB_URL, strict=True, echo=echo)

      logging.info(
          t.yellow(f"Falling back to local sqlite db: {SQLITE_FILE_DB_URL}"))
      return get_sql_engine(url=SQLITE_FILE_DB_URL, strict=False, echo=echo)


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
