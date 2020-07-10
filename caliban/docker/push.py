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

import subprocess


def _image_tag_for_project(project_id: str, image_id: str) -> str:
  """Generate the GCR Docker image tag for the supplied pair of project_id and
  image_id.

  This function properly handles "domain scoped projects", where the project ID
  contains a domain name and project ID separated by :
  https://cloud.google.com/container-registry/docs/overview#domain-scoped_projects.

  """
  project_s = project_id.replace(":", "/")
  return "gcr.io/{}/{}:latest".format(project_s, image_id)


def push_uuid_tag(project_id: str, image_id: str) -> str:
  """Takes a base image and tags it for upload, then pushes it to a remote Google
  Container Registry.

  Returns the tag on a successful push.

  TODO should this just check first before attempting to push if the image
  exists? Immutable names means that if the tag is up there, we're done.
  Potentially use docker-py for this.

  """
  image_tag = _image_tag_for_project(project_id, image_id)
  subprocess.run(["docker", "tag", image_id, image_tag], check=True)
  subprocess.run(["docker", "push", image_tag], check=True)
  return image_tag
