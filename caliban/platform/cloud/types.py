#!/usr/bin/python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Constants and types for GCloud interaction."""

import argparse
from enum import Enum
from typing import Callable, List, NamedTuple, Optional, Set, Union

import caliban.util as u


def _vfn(prefix: str) -> Callable[[str], str]:
  """Returns a function that prepends the supplied prefix and converts
  underscores to the dashes required by Cloud constants..

  """

  def inner(name: str) -> str:
    return "{}-{}".format(prefix, name.replace('_', '-'))

  return inner


US_REGIONS = {
    "west1",
    "west2",
    "west3",
    "central1",
    "east1",
    "east4",
}
NA_REGIONS = {
    "northeast1",
}
SA_REGIONS = {
    "east1",
}
EURO_REGIONS = {
    "west1",
    "west2",
    "west3",
    "west4",
    "west6",
    "north1",
}
ASIA_REGIONS = {
    "south1",
    "southeast1",
    "east1",
    "east2",
    "northeast1",
    "northeast2",
    "northeast3",
}
AUSTRALIA_REGIONS = {
    "southeast1",
}

# Actual enum types.
US = Enum('US', u.dict_by(US_REGIONS, _vfn("us")))
NorthAmerica = Enum('NorthAmerica', u.dict_by(NA_REGIONS, _vfn("northamerica")))
SouthAmerica = Enum('SouthAmerica', u.dict_by(SA_REGIONS, _vfn("southamerica")))
Europe = Enum('Europe', u.dict_by(EURO_REGIONS, _vfn("europe")))
Asia = Enum('Asia', u.dict_by(ASIA_REGIONS, _vfn("asia")))
Australia = Enum('Australia', u.dict_by(ASIA_REGIONS, _vfn("australia")))
Region = Union[US, NorthAmerica, SouthAmerica, Europe, Asia, Australia]
Zone = str


def valid_regions(zone: Optional[str] = None) -> List[Region]:
  """Returns valid region strings for Cloud, for the globe or for a particular
  region if specified.

  """
  if zone is None:
    return valid_regions("americas") \
      + valid_regions("europe") \
      + valid_regions("asia")
  z = zone.lower()
  if z == "americas":
    return list(US) + list(NorthAmerica) + list(SouthAmerica)
  elif z == "europe":
    return list(Europe)
  elif z == "asia":
    return list(Asia) + list(Australia)
  else:
    raise ValueError(
        "invalid zone: {}. Must be one of 'americas', 'europe', 'asia'.".format(
            zone))


# Machines types in Cloud's standard tier.
STANDARD_MACHINES = {
    "standard_4", "standard_8", "standard_16", "standard_32", "standard_64",
    "standard_96"
}

# Machines types in Cloud's high memory tier.
HIGHMEM_MACHINES = {
    "highmem_2", "highmem_4", "highmem_8", "highmem_16", "highmem_32",
    "highmem_64", "highmem_96"
}

# Machines types in Cloud's high CPU tier.
HIGHCPU_MACHINES = {"highcpu_16", "highcpu_32", "highcpu_64", "highcpu_96"}

# Machine types allowed if running in TPU mode.
TPU_MACHINES = {"cloud_tpu"}

# Machine types allowed in CPU or GPU modes.
NON_TPU_MACHINES = STANDARD_MACHINES.union(HIGHMEM_MACHINES).union(
    HIGHCPU_MACHINES)

# Type of physical machine available -> cloud name.
MachineType = Enum(
    'MachineType',
    u.merge(u.dict_by(NON_TPU_MACHINES, _vfn("n1")),
            u.dict_by(TPU_MACHINES, lambda s: s)))

# Various GPU types currently available on Cloud, mapped to their cloud
# identifiers.
GPU = Enum(
    "GPU", {
        "K80": "NVIDIA_TESLA_K80",
        "P4": "NVIDIA_TESLA_P4",
        "P100": "NVIDIA_TESLA_P100",
        "T4": "NVIDIA_TESLA_T4",
        "V100": "NVIDIA_TESLA_V100",
        "A100": "NVIDIA_TESLA_A100",
    })

# TPU types mapped from version to Cloud identifier.
TPU = Enum("TPU", {"V2": "TPU_V2", "V3": "TPU_V3"})

# Useful for typing functions; use this for functions that can handle either
# type of accelerator.
Accelerator = Union[GPU, TPU]

# Mapping between Accelerators and the regions where they're supported.
#
# From this page: https://cloud.google.com/ml-engine/docs/regions
#
# : Dict[Accelerator, Region]
ACCELERATOR_REGION_SUPPORT = {
    TPU.V2: [
        US.central1,
        Europe.west4,
    ],
    TPU.V3: [
        US.central1,
        Europe.west4,
    ],
    GPU.K80: [
        US.west1,
        US.central1,
        US.east1,
        Europe.west1,
        Asia.east1,
    ],
    GPU.P4: [
        US.west2,
        US.central1,
        US.east4,
        NorthAmerica.northeast1,
        Europe.west4,
        Asia.southeast1,
        Australia.southeast1,
    ],
    GPU.P100: [
        US.west1,
        US.central1,
        US.east1,
        SouthAmerica.east1,
        Europe.west1,
        Asia.east1,
        Australia.southeast1,
    ],
    GPU.T4: [
        US.west1,
        US.central1,
        US.east1,
        SouthAmerica.east1,
        Europe.west2,
        Europe.west4,
        Asia.south1,
        Asia.southeast1,
        Asia.northeast1,
        Asia.northeast3,
    ],
    GPU.V100: [
        US.west1,
        US.central1,
        Europe.west4,
        Asia.east1,
    ],
}

# Mapping between machine type and the Accelerator type and number of
# accelerators allowed on that particular machine type.
#
# From this page: https://cloud.google.com/ml-engine/docs/using-gpus
#
# and https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus
#
# : Dict[MachineType, Dict[Accelerator, Set[int]]]
COMPATIBILITY_TABLE = {
    MachineType.cloud_tpu: {
        TPU.V2: {8},
        TPU.V3: {8}
    },
    MachineType.standard_4: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8},
        GPU.A100: {0}
    },
    MachineType.standard_8: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8}
    },
    MachineType.standard_16: {
        GPU.K80: {2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {2, 4, 8}
    },
    MachineType.standard_32: {
        GPU.K80: {4, 8},
        GPU.P4: {2, 4},
        GPU.P100: {2, 4},
        GPU.T4: {2, 4},
        GPU.V100: {4, 8}
    },
    MachineType.standard_64: {
        GPU.P4: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    },
    MachineType.standard_96: {
        GPU.P4: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    },
    MachineType.highmem_2: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8}
    },
    MachineType.highmem_4: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8}
    },
    MachineType.highmem_8: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8}
    },
    MachineType.highmem_16: {
        GPU.K80: {2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {2, 4, 8}
    },
    MachineType.highmem_32: {
        GPU.K80: {4, 8},
        GPU.P4: {2, 4},
        GPU.P100: {2, 4},
        GPU.T4: {2, 4},
        GPU.V100: {4, 8}
    },
    MachineType.highmem_64: {
        GPU.P4: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    },
    MachineType.highmem_96: {
        GPU.P4: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    },
    MachineType.highcpu_16: {
        GPU.K80: {2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {2, 4, 8}
    },
    MachineType.highcpu_32: {
        GPU.K80: {4, 8},
        GPU.P4: {2, 4},
        GPU.P100: {2, 4},
        GPU.T4: {2, 4},
        GPU.V100: {4, 8}
    },
    MachineType.highcpu_64: {
        GPU.K80: {8},
        GPU.P4: {4},
        GPU.P100: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    },
    MachineType.highcpu_96: {
        GPU.P4: {4},
        GPU.T4: {4},
        GPU.V100: {8}
    }
}

# : Dict[Accelerator, Dict[MachineType, Set[int]]]
_AccelMTCount = u.reorderm(COMPATIBILITY_TABLE, (1, 0, 2))

# : Dict[Accelerator, Dict[int, Set[MachineType]]]
_AccelCountMT = u.reorderm(COMPATIBILITY_TABLE, (1, 2, 0))


def accelerator_name(is_gpu: bool) -> str:
  return "GPU" if is_gpu else "TPU"


def with_advice_suffix(accel: Union[Accelerator, str], s: str) -> str:
  """Accepts either an accelerator instance or a string as its first arg (the str
  can be 'gpu' or 'tpu', or any cased version of those) and a message string.

  Returns a string with a suffix appended that links to the GPU or CPU
  breakdown page, depending on the accelerator type.

  """
  if isinstance(accel, str):
    is_gpu = accel.upper() == 'GPU'
  else:
    is_gpu = accel in GPU

  ucase = accelerator_name(is_gpu)

  if is_gpu:
    url = "https://cloud.google.com/ml-engine/docs/using-gpus"
  else:
    url = "https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus"

  return """{s}
For more help, consult this page for valid combinations of {ucase} count, {ucase} type and machine type:
{url}
""".format_map({
      "s": s,
      "ucase": ucase,
      "url": url
  })


def accelerator_counts(accel: Accelerator,
                       machine_type: Optional[MachineType] = None) -> Set[int]:
  """Returns the set of Accelerator count numbers valid for the supplied machine
  type.

  If machine_type is None, returns the set of valid counts for the supplied
  accelerator on ANY machine type.

  """
  ret = set()
  for mt, counts in _AccelMTCount[accel].items():
    if machine_type is None or mt == machine_type:
      ret = ret.union(counts)

  return ret


def validate_accelerator_count(accel: Accelerator, count: int) -> int:
  """Raises an error if the count isn't valid for the supplied accelerator, else
  returns the count.

  """
  is_gpu = accel in GPU
  ucase = accelerator_name(is_gpu)
  valid_counts = accelerator_counts(accel)
  if not _AccelCountMT[accel].get(count):
    raise argparse.ArgumentTypeError(
        with_advice_suffix(
            accel, "{} {}s of type {} aren't available \
for any machine type. Try one of the following counts: {}\n".format(
                count, ucase, accel.name, valid_counts)))

  return count


def parse_machine_type(s: str) -> MachineType:
  """Attempts to parse the string into a valid machine type; raises a sensible
  argparse error if that's not possible.

  """
  try:
    return MachineType(s)
  except ValueError:
    valid_values = u.enum_vals(MachineType)
    raise argparse.ArgumentTypeError("'{}' isn't a valid machine type. \
Must be one of {}.".format(s, valid_values))


def parse_region(s: str) -> Region:
  """Attempts to parse the string into a valid region; raises a sensible argparse
  error if that's not possible.

  """
  try:
    return u.any_of(s, Region)
  except ValueError:
    valid_values = u.enum_vals(valid_regions())
    raise argparse.ArgumentTypeError("'{}' isn't a valid region. \
Must be one of {}.".format(s, valid_values))


def parse_accelerator_arg(s: str,
                          mode: str,
                          suffix: str,
                          validate_count: bool = True):
  mode = mode.upper()
  assert mode in ("GPU", "TPU"), "Mode must be GPU or TPU."

  items = s.split("x")

  if len(items) != 2:
    raise argparse.ArgumentTypeError(
        with_advice_suffix(
            mode,
            "{} arg '{}' has no 'x' separator.\n{}".format(mode, s, suffix)))

  count_s, type_s = items

  count = None
  accelerator_type = None

  # Check that the number can parse at all.
  try:
    count = int(count_s)
  except ValueError:
    raise argparse.ArgumentTypeError(
        with_advice_suffix(
            mode, "The count '{}' isn't a number!\n{}".format(count_s, suffix)))

  # Validate that we have a valid GPU type.
  try:
    accel_dict = GPU if mode == "GPU" else TPU
    accelerator_type = accel_dict[type_s.upper()]

  except KeyError:
    all_types = list(map(lambda s: s.name, accel_dict))
    raise argparse.ArgumentTypeError(
        with_advice_suffix(
            mode, "'{}' isn't a valid {} type. Must be one of {}.\n".format(
                type_s, mode, all_types)))

  if validate_count:
    validate_accelerator_count(accelerator_type, count)

  return accelerator_type, count


class GPUSpec(NamedTuple('GPUSpec', [("gpu", GPU), ("count", int)])):
  """Info to generate a GPU."""

  METAVAR = "NUMxGPU_TYPE"
  _error_suffix = "You must supply a string of the format {}. \
8xV100, for example.\n".format(METAVAR)

  @staticmethod
  def parse_arg(s: str, **kwargs) -> "GPUSpec":
    """Parses a CLI string of the form COUNTxGPUType into a proper GPU spec
    instance.

    """
    gpu, count = parse_accelerator_arg(s, "GPU", GPUSpec._error_suffix,
                                       **kwargs)
    return GPUSpec(gpu, count)

  @property
  def accelerator_type(self):
    return accelerator_name(True)

  @property
  def name(self):
    return self.gpu.name

  def accelerator_config(self):
    return {"type": self.gpu.value, "count": self.count}

  def allowed_machine_types(self) -> Set[MachineType]:
    """Set of all machine types allowed for this particular combination.

    """
    return _AccelCountMT[self.gpu].get(self.count, {})

  def allowed_regions(self) -> Set[Region]:
    """Set of all regions allowed for this particular GPU type.

    """
    return set(ACCELERATOR_REGION_SUPPORT[self.gpu])

  def valid_machine_type(self, machine_type: MachineType) -> bool:
    return machine_type in self.allowed_machine_types()

  def valid_region(self, region: Region) -> bool:
    return region in self.allowed_regions()


class TPUSpec(NamedTuple('TPUSpec', [("tpu", TPU), ("count", int)])):
  """Info to generate a TPU."""

  METAVAR = "NUMxTPU_TYPE"
  _error_suffix = "You must supply a string of the format {}. \
8xV2, for example.".format(METAVAR)

  @staticmethod
  def parse_arg(s: str, **kwargs) -> "TPUSpec":
    """Parses a CLI string of the form COUNTxGPUType into a proper GPU spec
    instance.

    """
    tpu, count = parse_accelerator_arg(s, "TPU", TPUSpec._error_suffix,
                                       **kwargs)
    return TPUSpec(tpu, count)

  @property
  def accelerator_type(self):
    return accelerator_name(False)

  @property
  def name(self):
    return self.tpu.name

  def accelerator_config(self):
    return {"type": self.tpu.value, "count": self.count}

  def allowed_machine_types(self) -> Set[MachineType]:
    """Set of all machine types allowed for this combo."""
    return _AccelCountMT[self.tpu].get(self.count, {})

  def allowed_regions(self) -> Set[Region]:
    """Set of all regions allowed for this particular TPU type.

    """
    return set(ACCELERATOR_REGION_SUPPORT[self.tpu])

  def valid_machine_type(self, machine_type: MachineType) -> bool:
    return machine_type in self.allowed_machine_types()

  def valid_region(self, region: Region) -> bool:
    return region in self.allowed_regions()


# ----------------------------------------------------------------------------
# CAIP job status, see:
# https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/projects.jobs#Job
# https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/projects.jobs#State
class JobStatus(Enum):
  STATE_UNSPECIFIED = 'STATE_UNSPECIFIED'
  QUEUED = 'QUEUED'
  PREPARING = 'PREPARING'
  RUNNING = 'RUNNING'
  SUCCEEDED = 'SUCCEEDED'
  FAILED = 'FAILED'
  CANCELLING = 'CANCELLING'
  CANCELLED = 'CANCELLED'

  def is_terminal(self) -> bool:
    return self.value in ['SUCCEEDED', 'FAILED', 'CANCELLED']
