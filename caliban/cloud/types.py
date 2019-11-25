"""Constants and types for GCloud interaction."""

from __future__ import annotations

import argparse
from enum import Enum
from typing import (Any, Callable, Dict, Iterable, List, NamedTuple, Optional,
                    Set, Tuple, Union)

import caliban.util as u


def _vfn(prefix: str) -> Callable[[str], str]:
  """Returns a function that prepends the supplied prefix and converts
  underscores to the dashes required by Cloud constants..

  """

  def inner(name: str) -> str:
    return f"{prefix}-{name.replace('_', '-')}"

  return inner


US_REGIONS: Set[str] = {"west1", "west2", "central1", "east1", "east4"}
EURO_REGIONS: Set[str] = {"west1", "west4", "north1"}
ASIA_REGIONS: Set[str] = {"southeast1", "east1", "northeast1"}

# Actual enum types.
US = Enum('US', u.dict_by(US_REGIONS, _vfn("us")))
Europe = Enum('Europe', u.dict_by(EURO_REGIONS, _vfn("europe")))
Asia = Enum('Asia', u.dict_by(ASIA_REGIONS, _vfn("asia")))
Region = Union[US, Europe, Asia]

# Machines types in Cloud's standard tier.
STANDARD_MACHINES: Set[str] = {
    "standard_4", "standard_8", "standard_16", "standard_32", "standard_64",
    "standard_96"
}

# Machines types in Cloud's high memory tier.
HIGHMEM_MACHINES: Set[str] = {
    "highmem_2", "highmem_4", "highmem_8", "highmem_16", "highmem_32",
    "highmem_64", "highmem_96"
}

# Machines types in Cloud's high CPU tier.
HIGHCPU_MACHINES: Set[str] = {
    "highcpu_16", "highcpu_32", "highcpu_64", "highcpu_96"
}

# Machine types allowed if running in TPU mode.
TPU_MACHINES: Set[str] = {"cloud_tpu"}

# Machine types allowed in CPU or GPU modes.
NON_TPU_MACHINES: Set[str] = STANDARD_MACHINES.union(HIGHMEM_MACHINES).union(
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
        "V100": "NVIDIA_TESLA_V100"
    })

# TPU types mapped from version to Cloud identifier.
TPU = Enum(
    "TPU",
    {
        "V2": "TPU_V2",
        # NOTE - V3 are only available in beta for now.
        "V3": "TPU_V3"
    })

# Useful for typing functions; use this for functions that can handle either
# type of accelerator.
Accelerator = Union[GPU, TPU]

# Mode
JobMode = Enum("JobMode", ("CPU", "GPU", "TPU"))

# Mapping between Accelerators and the regions where they're supported.
#
# From this page: https://cloud.google.com/ml-engine/docs/regions
#
ACCELERATOR_REGION_SUPPORT: Dict[Accelerator, Region] = {
    TPU.V2: [US.central1],
    TPU.V3: [US.central1],
    GPU.K80: [US.west1, US.central1, US.east1, Europe.west1, Asia.east1],
    GPU.P4: [US.west2, US.central1, US.east4, Europe.west4, Asia.southeast1],
    GPU.P100: [US.west1, US.central1, US.east1, Europe.west1, Asia.east1],
    GPU.T4: [US.west1, US.central1, US.east1, Europe.west4, Asia.southeast1],
    GPU.V100: [US.west1, US.central1, Europe.west4, Asia.east1],
}

# Mapping between machine type and the Accelerator type and number of
# accelerators allowed on that particular machine type.
#
# From this page: https://cloud.google.com/ml-engine/docs/using-gpus
#
# and https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus
#
COMPATIBILITY_TABLE: Dict[MachineType, Dict[Accelerator, Set[int]]] = {
    MachineType.cloud_tpu: {
        TPU.V2: {8},
        TPU.V3: {8}
    },
    MachineType.standard_4: {
        GPU.K80: {1, 2, 4, 8},
        GPU.P4: {1, 2, 4},
        GPU.P100: {1, 2, 4},
        GPU.T4: {1, 2, 4},
        GPU.V100: {1, 2, 4, 8}
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

_AccelMTCount: Dict[Accelerator, Dict[MachineType, Set[int]]] = u.reorderm(
    COMPATIBILITY_TABLE, (1, 0, 2))

_AccelCountMT: Dict[Accelerator, Dict[int, Set[MachineType]]] = u.reorderm(
    COMPATIBILITY_TABLE, (1, 2, 0))


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
  type_s = "GPU" if accel in GPU else "TPU"
  valid_counts = accelerator_counts(accel)
  if not _AccelCountMT[accel].get(count):
    raise argparse.ArgumentTypeError(
        with_gpu_advice_suffix(
            f"{count} {type_s}s of type {accel.name} aren't available \
for any machine type. Try one of the following counts: {valid_counts}"))

  return count


def parse_machine_type(s: str) -> MachineType:
  """Attempts to parse the string into a valid machine type; raises a sensible
  argparse error if that's not possible.

  """
  try:
    return MachineType(s)
  except ValueError:
    valid_values = set(map(lambda s: s.value, MachineType))
    raise argparse.ArgumentTypeError(f"'{s}' isn't a valid machine type. \
Must be one of {valid_values}.")


def _advice_suffix(accelerator_type: str, url: str, s: str) -> str:
  ucase = accelerator_type.upper()
  return f"""{s}

For more help, consult this page for valid combinations of {ucase} count, {ucase} type and machine type:
{url}
"""


def with_gpu_advice_suffix(s: str) -> str:
  """Appends a suffix with a link to the GPU breakdown page."""
  url = "https://cloud.google.com/ml-engine/docs/using-gpus"
  return _advice_suffix("gpu", url, s)


def with_tpu_advice_suffix(s: str) -> str:
  """Appends a suffix with a link to the TPU breakdown page."""
  url = "https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus"
  return _advice_suffix("tpu", url, s)


class GPUSpec(NamedTuple):
  """Info to generate a GPU."""
  gpu: GPU
  count: int

  METAVAR = "NUMxGPU_TYPE"
  _error_suffix = f"You must supply a string of the format {METAVAR}. \
8xV100, for example."

  @staticmethod
  def parse_arg(s: str) -> GPUSpec:
    """Parses a CLI string of the form COUNTxGPUType into a proper GPU spec
    instance.

    """
    items = s.split("x")
    if len(items) != 2:
      raise argparse.ArgumentTypeError(
          with_gpu_advice_suffix(f"GPU arg '{s}' has no 'x' separator.\n" +
                                 GPUSpec._error_suffix))

    count_s, type_s = items
    count = None
    gpu_type = None

    # Check that the number can parse at all.
    try:
      count = int(count_s)
    except ValueError:
      raise argparse.ArgumentTypeError(
          with_gpu_advice_suffix(f"The count '{count_s}' isn't a number!\n" +
                                 GPUSpec._error_suffix))

    # Validate that we have a valid GPU type.
    try:
      gpu_type = GPU[type_s.upper()]
    except KeyError:
      all_types = list(map(lambda s: s.name, GPU))
      raise argparse.ArgumentTypeError(
          with_gpu_advice_suffix(
              f"""'{type_s}' isn't a valid GPU type. Must be one of {all_types}.\n
          """))

    validate_accelerator_count(gpu_type, count)

    return GPUSpec(gpu_type, count)

  def accelerator_config(self):
    return {"type": self.gpu.value, "count": self.count}

  def allowed_machine_types(self) -> Set[MachineType]:
    """Set of all machine types allowed for this particular combination.

    """
    return _AccelCountMT[self.gpu].get(self.count, {})

  def allowed_regions(self) -> Set[str]:
    """Set of all regions allowed for this particular GPU type.

    """
    return set(ACCELERATOR_REGION_SUPPORT[self.gpu])

  def valid_machine_type(self, machine_type: MachineType) -> bool:
    return machine_type in self.allowed_machine_types()

  def valid_region(self, region: str) -> bool:
    return region in self.allowed_regions()


class TPUSpec(NamedTuple):
  """Info to generate a TPU. Count has to be 8!

  This is of course quite similar to GPUSpec above. There are much more
  stringent requirements on TPUs, so I'm expecting that this class will develop
  more specific methods.

  """
  tpu: TPU
  count: int

  def accelerator_config(self):
    return {"type": self.tpu.value, "count": self.count}

  def allowed_machine_types(self) -> Set[str]:
    """Set of all machine types allowed for this combo."""
    return _AccelCountMT[self.tpu].get(self.count, {})

  def allowed_regions(self) -> Set[str]:
    """Set of all regions allowed for this particular TPU type.

    """
    return set(ACCELERATOR_REGION_SUPPORT[self.tpu])

  def valid_machine_type(self, machine_type: MachineType) -> bool:
    return machine_type in self.allowed_machine_types()

  def valid_region(self, region: str) -> bool:
    return region in self.allowed_regions()
