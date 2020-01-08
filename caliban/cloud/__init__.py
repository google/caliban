"""Hypothesis is a library for writing unit tests which are parametrized by
some source of data.
It verifies your code against a wide range of input and minimizes any
failing examples it finds.
"""

from __future__ import absolute_import, division, print_function

from caliban.cloud.core import submit_ml_job, generate_image_tag
from caliban.cloud.types import (GPUSpec, Region, TPUSpec, parse_region,
                                 valid_regions)

__all__ = [
    "GPUSpec",
    "parse_region",
    "Region",
    "submit_ml_job",
    "TPUSpec",
    "valid_regions",
    "generate_image_tag",
]
