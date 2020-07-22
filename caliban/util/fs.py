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
import io
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from typing import List, NamedTuple, Optional

from blessings import Terminal

t = Terminal()

Package = NamedTuple("Package", [("executable", List[str]),
                                 ("package_path", str), ("script_path", str),
                                 ("main_module", Optional[str])])


def file_exists_in_cwd(path: str) -> bool:
  """Returns True if the current path references a valid file in the current
  directory, False otherwise.

  """
  return os.path.isfile(os.path.join(os.getcwd(), path))


def extract_root_directory(path: str) -> str:
  """Returns the root directory of the supplied path."""
  items = path.split(os.path.sep)
  return "." if len(items) == 1 else items[0]


def module_package(main_module: str) -> Package:
  """Generates a Package instance for a python module executable that should be
  executed with python -m.

  """
  script_path = module_to_path(main_module)
  root = extract_root_directory(script_path)
  return Package(["python", "-m"],
                 package_path=root,
                 script_path=script_path,
                 main_module=main_module)


def script_package(path: str, executable: str = "/bin/bash") -> Package:
  """Generates a Package instance for a non-python-module executable."""
  root = extract_root_directory(path)
  return Package([executable],
                 package_path=root,
                 script_path=path,
                 main_module=None)


def path_to_module(path_str: str) -> str:
  return path_str.replace(".py", "").replace(os.path.sep, ".")


def module_to_path(module_name: str) -> str:
  """Converts the supplied python module (module names separated by dots) into
  the python file represented by the module name.

  """
  return module_name.replace(".", os.path.sep) + ".py"


def generate_package(path: str,
                     executable: Optional[List[str]] = None,
                     main_module: Optional[str] = None) -> Package:
  """Takes in a string and generates a package instance that we can use for
  imports.
  """
  if executable is None:
    _, ext = os.path.splitext(path)
    executable = ["python"] if ext == ".py" else ["/bin/bash"]

  if main_module is None and not file_exists_in_cwd(path):
    module_path = module_to_path(path)

    if file_exists_in_cwd(module_path):
      return generate_package(module_path,
                              executable=["python", "-m"],
                              main_module=path_to_module(module_path))

  root = extract_root_directory(path)
  return Package(executable, root, path, main_module)


class TempCopy(object):
  """Inside its scope, this class:

  - generates a temporary file at tmp_name containing a copy of the file at
    original_path, and
  - deletes the new file at tmp_name when the scope exits.

  The temporary file will live inside the current directory where python's
  being executed; it's a hidden file, but it will be live for the duration of
  TempCopy's scope.

  We did NOT use a tmp directory here because the changing UUID name
  invalidates the docker image each time a new temp path / directory is
  generated.

  """

  def __init__(self, original_path=None, tmp_name=None):
    if tmp_name is None:
      self.tmp_path = ".{}.json".format(str(uuid.uuid1()))
    else:
      self.tmp_path = tmp_name

    self.original_path = None
    if original_path:
      # handle tilde!
      self.original_path = os.path.expanduser(original_path)

    self.path = None

  def __enter__(self):
    if self.original_path is None:
      return None

    current_dir = os.getcwd()
    self.path = os.path.join(current_dir, self.tmp_path)
    shutil.copy2(self.original_path, self.path)
    return self.tmp_path

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.path is not None:
      os.remove(self.path)
      self.path = None


def capture_stdout(cmd: List[str],
                   input_str: Optional[str] = None,
                   file=None) -> str:
  """Executes the supplied command with the supplied string of std input, then
  streams the output to stdout, and returns it as a string along with the
  process's return code.

  Args:
  cmd: list of strings to send in as the command
  input_str: if supplied, this string will be passed as stdin to the supplied
             command. if None, stdin will get closed immediately.
  file: optional file-like object (stream): the output from the executed
        process's stdout will get sent to this stream. Defaults to sys.stdout.

  Returns:
  Pair of
  - string of all stdout received during the command's execution
  - return code of the process

  """
  if file is None:
    file = sys.stdout

  buf = io.StringIO()
  ret_code = None

  with subprocess.Popen(cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=False,
                        bufsize=1) as p:
    if input_str:
      p.stdin.write(input_str.encode('utf-8'))
    p.stdin.close()

    out = io.TextIOWrapper(p.stdout, newline='')

    for line in out:
      buf.write(line)
      file.write(line)
      file.flush()

    # flush to force the contents to display.
    file.flush()

    while p.poll() is None:
      # Process hasn't exited yet, let's wait some
      time.sleep(0.5)

    ret_code = p.returncode
    p.stdout.close()

  return buf.getvalue(), ret_code


def next_free_port(port: int, try_n: int = 1000, max_port=65535):
  if try_n == 0 or port <= max_port:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      sock.bind(('', port))
      sock.close()
      return port
    except OSError:
      return next_free_port(port + 1, try_n - 1, max_port=max_port)
  else:
    raise IOError('no free ports')
