'''types for caliban.history'''

from enum import Enum
from caliban.gke.types import JobStatus as GkeStatus
from caliban.cloud.types import JobStatus as CloudStatus
from typing import Union

JobStatus = Union[GkeStatus, CloudStatus]


# ----------------------------------------------------------------------------
class Platform(Enum):
  '''execution platforms'''
  CAIP = 'Cloud AI Platform'
  GKE = 'Google Kubernetes Engine'
  LOCAL = 'Local'
