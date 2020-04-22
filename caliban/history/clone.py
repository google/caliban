'''utilities for cloning runs for specific compute backends'''

from copy import deepcopy

from caliban.history.types import SubmissionStatus, Platform, TestJobStatus
from caliban.history.interfaces import Run
import caliban.history.null_compute


# ----------------------------------------------------------------------------
def clone_run(r: Run) -> SubmissionStatus:
  '''
  Clone a Run.

  This recreates a run as exactly as possible on the same backend compute
  platform. This uses the same container and all parameters settings, along
  with any compute-platform specific parameters to perform as close to an
  identical run as possible.

  This takes the run spec returned from the previous Run instance to
  submit to the backend.
  '''
  if r.platform() == Platform.TEST:
    return SubmissionStatus(spec=deepcopy(r.spec()),
                            status=TestJobStatus.SUBMITTED)

  # todo: implement for other backends
  assert False, f'clone_run not implemented for {f.platform().name}'
