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
'''caliban utilities for job re-submission'''

from typing import List, Optional

import caliban.platform.cloud.core as cloud
import caliban.platform.gke.cli as gke_cli
import caliban.platform.run as r
from caliban.history.types import JobSpec, Platform


# ----------------------------------------------------------------------------
def submit_job_specs(
    specs: List[JobSpec],
    platform: Platform,
    project_id: Optional[str] = None,
    credentials_path: Optional[str] = None,
) -> None:
  '''submits a job spec'''

  if len(specs) == 0:
    return

  if platform == Platform.LOCAL:
    return r.execute_jobs(job_specs=specs)

  if platform == Platform.CAIP:
    return cloud.submit_job_specs(
        specs=specs,
        project_id=project_id,
        credentials_path=credentials_path,
        num_specs=len(specs),
    )

  if platform == Platform.GKE:
    return gke_cli.submit_job_specs(args={
        'cloud_key': credentials_path,
        'project_id': project_id,
        'specs': specs,
    },)

  return None
