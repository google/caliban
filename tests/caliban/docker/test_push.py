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

import caliban.docker.push as p


def register_list_tags(process, project_id, tag, **kwargs):
  process.register_subprocess([
      "gcloud", "container", "images", "list-tags", f"--project={project_id}",
      "--format=json", tag
  ], **kwargs)


def test_image_tag_for_project():
  """Tests that we generate a valid image tag for domain-scoped and modern
    project IDs.

    """
  assert p._image_tag_for_project("face",
                                  "imageid") == "gcr.io/face/imageid:latest"

  assert p._image_tag_for_project(
      "google.com:face", "imageid") == "gcr.io/google.com/face/imageid:latest"


def test_force_push_uuid_tag(fake_process):
  """Check that the push command actually attempts to tag and push."""
  project_id = "project"
  image_id = "imageid"

  tag = p._image_tag_for_project(project_id, image_id)

  fake_process.register_subprocess(["docker", "tag", image_id, tag])
  fake_process.register_subprocess(["docker", "push", tag])

  assert p.push_uuid_tag(project_id, image_id, force=True) == tag


def test_already_pushed_uuid_tag(fake_process):
  """Check that push_uuid_tag does NOT attempt to push if the process already
  exists.."""
  project_id = "project"
  image_id = "imageid"

  base_tag = p._image_tag_for_project(project_id, image_id, include_tag=False)
  tag = p._image_tag_for_project(project_id, image_id)

  register_list_tags(fake_process,
                     project_id,
                     base_tag,
                     stdout="[{\"metadata\": []}]")

  assert p.push_uuid_tag(project_id, image_id) == tag


def test_push_uuid_tag_if_no_remote_image(fake_process):
  """Check that push_uuid_tag DOES attempt to push if the image doesn't exist in
  the remote container registry already.

  """
  project_id = "project"
  image_id = "imageid"

  base_tag = p._image_tag_for_project(project_id, image_id, include_tag=False)
  tag = p._image_tag_for_project(project_id, image_id)

  register_list_tags(fake_process, project_id, base_tag, stdout="[]")

  fake_process.register_subprocess(["docker", "tag", image_id, tag])
  fake_process.register_subprocess(["docker", "push", tag])

  assert p.push_uuid_tag(project_id, image_id) == tag
