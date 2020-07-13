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

from subprocess import CalledProcessError

from google.oauth2.credentials import Credentials

import caliban.util.auth as a


def register_auth(process, **kwargs):
  process.register_subprocess(["gcloud", "auth", "print-access-token"],
                              **kwargs)


def fail_process(process):
  process.returncode = 1
  raise CalledProcessError("cmd", "exception! Not logged in!")


def test_auth_access_token(fake_process):
  """Check that if the user has logged in with `gcloud auth login`,
  `auth_access_token` returns the correct token.

  """
  token = "token"
  register_auth(fake_process, stdout=token)
  assert a.auth_access_token() == token


def test_missing_auth_access_token(fake_process):
  """Check that if the user has NOT logged in with `gcloud auth login`,
  `auth_access_token` returns None.

  """
  register_auth(fake_process, callback=fail_process)
  assert a.auth_access_token() is None


def test_gcloud_auth_credentials(fake_process):
  """Check that if the user has logged in with `gcloud auth login`,
  a proper instance of Credentials is returned.

  """
  token = "token"
  register_auth(fake_process, stdout=token)
  assert isinstance(a.gcloud_auth_credentials(), Credentials)


def test_missing_gcloud_auth_credentials(fake_process):
  """Check that if the user has logged in with `gcloud auth login`,
  `auth_access_token` returns the correct token.

  """
  register_auth(fake_process, callback=fail_process)
  assert a.gcloud_auth_credentials() is None
