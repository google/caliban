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

import caliban.docker.build as b


def test_shell_dict():
  """Tests that the shell dict has an entry for all possible Shell values."""

  assert set(b.Shell) == set(b.SHELL_DICT.keys())


def test_copy_command():
  multiline = b.copy_command(1, 1, "face", "cake",
                             "This is an example\nof a multiline comment.")

  assert multiline == f"""# This is an example
# of a multiline comment.
COPY --chown=1:1 face cake
"""

  # single lines don't append comments.
  oneline = b.copy_command(1, 1, "face", "cake.py")
  assert oneline == """COPY --chown=1:1 face cake.py
"""

  # single comments work.
  oneline_comment = b.copy_command(1, 1, "face", "cake.py", comment="Comment!")
  assert oneline_comment == f"""# Comment!
COPY --chown=1:1 face cake.py
"""
