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
"""Utilities for interacting with the filesystem and packages.

"""

from subprocess import CalledProcessError, check_output
from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials


def auth_access_token() -> Optional[str]:
  """Attempts to fetch the local Oauth2 access token from the user's environment.
  Returns the token if it exists, or None if not

  """
  try:
    ret = check_output(['gcloud', 'auth', 'print-access-token'],
                       encoding='utf8').rstrip()
    return ret if len(ret) > 0 else None
  except CalledProcessError:
    return None


def gcloud_auth_credentials() -> Optional[Credentials]:
  """Attempt to generate credentials from the oauth2 workflow triggered by
  `gcloud auth login`. Returns

  """
  token = auth_access_token()
  if token:
    return Credentials(token)


def gcloud_credentials(
    credentials_path: Optional[str] = None) -> Optional[Credentials]:
  credentials = None

  if credentials_path is not None:
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path)
  else:
    # attempt to fetch credentials acquired via `gcloud auth login`. If this
    # fails, the following API object will attempt to use application default
    # credentials.
    credentials = gcloud_auth_credentials()

    return credentials
