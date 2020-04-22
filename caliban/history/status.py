'''utilities for retreiving run status from specific backends'''

from caliban.history.interfaces import Run
from caliban.history.types import JobStatus, Platform
import caliban.history.null_compute


# ----------------------------------------------------------------------------
def get_run_status(r: Run) -> JobStatus:
  '''get run status from compute platform backend

  Args:
  r: Run instance

  Returns:
  JobStatus
  '''
  if r.platform() == Platform.TEST:
    return caliban.history.null_compute.get_status(r)

  # todo: implement for other backends
  assert False, f'get_run_status not implemented for {r.platform().name}'
