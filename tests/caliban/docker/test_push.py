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


def test_image_tag_for_project():
  """Tests that we generate a valid image tag for domain-scoped and modern
    project IDs.

    """
  assert p._image_tag_for_project("face",
                                  "imageid") == "gcr.io/face/imageid:latest"

  assert p._image_tag_for_project(
      "google.com:face", "imageid") == "gcr.io/google.com/face/imageid:latest"
