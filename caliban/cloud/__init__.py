"""Hypothesis is a library for writing unit tests which are parametrized by
some source of data.
It verifies your code against a wide range of input and minimizes any
failing examples it finds.
"""

from __future__ import absolute_import, division, print_function

from caliban.cloud.core import (DEFAULT_GPU, DEFAULT_MACHINE_TYPE,
                                DEFAULT_REGION, DRY_RUN_FLAG, submit_ml_job)
from caliban.cloud.types import JobMode, Region, parse_region, valid_regions

__all__ = [
    "DEFAULT_GPU",
    "DEFAULT_MACHINE_TYPE",
    "DEFAULT_REGION",
    "DRY_RUN_FLAG",
    "JobMode",
    "parse_region",
    "Region",
    "submit_ml_job",
    "valid_regions",
]
