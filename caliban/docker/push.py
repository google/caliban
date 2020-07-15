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
"""Functions required to interact with Docker to build and run images, shells
and notebooks in a Docker environment.

"""

import json
import subprocess

from absl import logging


def _image_tag_for_project(project_id: str,
                           image_id: str,
                           include_tag: bool = True) -> str:
  """Generate the GCR Docker image tag for the supplied pair of project_id and
  image_id.

  This function properly handles "domain scoped projects", where the project ID
  contains a domain name and project ID separated by :
  https://cloud.google.com/container-registry/docs/overview#domain-scoped_projects.

  """
  project_s = project_id.replace(":", "/")
  base = f"gcr.io/{project_s}/{image_id}"
  return f"{base}:latest" if include_tag else base


def _gcr_list_tags(project_id: str, image_id: str):
  """Returns a sequence of metadata for all tags of the supplied image_id in the
  supplied project.

  """
  image_tag = _image_tag_for_project(project_id, image_id, include_tag=False)
  cmd = [
      "gcloud", "container", "images", "list-tags", f"--project={project_id}",
      "--format=json", image_tag
  ]
  return json.loads(subprocess.check_output(cmd))


def gcr_image_pushed(project_id: str, image_id: str) -> bool:
  """Returns true if the supplied image has been pushed to the container registry
  for the supplied project, false otherwise.

  """
  return len(_gcr_list_tags(project_id, image_id)) > 0


def push_uuid_tag(project_id: str, image_id: str, force: bool = False) -> str:
  """Takes a base image and tags it for upload, then pushes it to a remote Google
  Container Registry.

  Returns the tag on a successful push.
  """
  image_tag = _image_tag_for_project(project_id, image_id)

  def missing_remotely():
    missing = not gcr_image_pushed(project_id, image_id)
    if not missing:
      logging.info(
          f"Skipping docker push, as {image_tag} already exists remotely.")
    return missing

  if force or missing_remotely():
    subprocess.run(["docker", "tag", image_id, image_tag], check=True)
    subprocess.run(["docker", "push", image_tag], check=True)

  return image_tag
