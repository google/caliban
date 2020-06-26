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
"""
Utilities for our job runner.
"""
import argparse
import contextlib
import getpass
import io
import itertools as it
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from collections import ChainMap
from enum import Enum
from typing import (Any, Callable, Dict, Iterable, List, NamedTuple, Optional,
                    Set, Tuple, Union)

import tqdm
from absl import logging
from blessings import Terminal
from tqdm._utils import _term_move_up

t = Terminal()

# key and value for labels can be at most this-many-characters long.
AI_PLATFORM_MAX_LABEL_LENGTH = 63

Package = NamedTuple("Package", [("executable", List[str]),
                                 ("package_path", str), ("script_path", str),
                                 ("main_module", Optional[str])])


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


def err(s: str) -> None:
  """Prints the supplied string to stderr in red text."""
  sys.stderr.write(t.red(s))


def current_user() -> str:
  return getpass.getuser()


def is_mac() -> bool:
  """Returns True if the current code is executing on a Mac, False otherwise.

  """
  return platform.system() == "Darwin"


def is_linux() -> bool:
  """Returns True if the current code is executing on a Linux system, False
  otherwise.

  """
  return platform.system() == "Darwin"


def enum_vals(enum: Enum) -> List[str]:
  """Returns the list of all values for a specific enum."""
  return [v.value for v in enum]


def any_of(value_s: str, union_type: Union) -> Any:
  """Attempts to parse the supplied string into one of the components of the
  supplied Union. Returns the value if possible, else raises a value error.

  union_type must be a union of enums!

  """

  def attempt(s: str, enum_type: Enum) -> Optional[Any]:
    try:
      return enum_type(s)
    except ValueError:
      return None

  enums = union_type.__args__
  ret = None

  for enum_type in enums:
    ret = attempt(value_s, enum_type)
    if ret is not None:
      break

  if ret is None:
    raise ValueError("{} isn't a value of any of {}".format(value_s, enums))

  return ret


def _expand_compound_pair(k: Union[Tuple, str], v: Any) -> Dict:
  """ given a key-value pair k v, where k is either:
      a) a primitive representing a single, e.g. k = 'key', v = 'value', or
      b) a tuple of primitives representing multiple keys, e.g. k = ('key1','key2'), v = ('value1', 'value2')
      this function returns the corresponding dictionary without compound keys
  """

  if isinstance(k, tuple):
    if not isinstance(v, tuple):
      raise argparse.ArgumentTypeError(
          """function _expand_compound_pair(k, v) requires that if type(k) is tuple,
             type(v) must also be tuple.""")
    else:
      return dict(zip(k, v))
  else:
    return {k: v}


def expand_compound_dict(m: Union[Dict, List]) -> Union[Dict, List]:
  """ given a dictionary with some compound keys, aka tuples,
  returns a dictionary which each compound key separated into primitives

  given a list of such dictionaries, will apply the transformation
  described above to each dictionary and return the list, maintaining
  structure
  """

  if isinstance(m, list):
    return [expand_compound_dict(mi) for mi in m]
  else:
    expanded_dicts = [_expand_compound_pair(k, v) for k, v in m.items()]
    return dict(ChainMap(*expanded_dicts))


def tupleize_dict(m: Dict) -> Dict:
  """ given a dictionary with compound keys, converts those keys to tuples, and
  converts the corresponding values to a tuple or list of tuples

  Compound key: a string which uses square brackets to enclose
  a comma-separated list, e.g. "[batch_size,learning_rate]" or "[a,b,c]"
  """

  formatted_items = [_tupleize_compound_item(k, v) for k, v in m.items()]
  return dict(ChainMap(*formatted_items))


def _tupleize_compound_item(k: Union[Tuple, str], v: Any) -> Dict:
  """ converts a JSON-input compound key/value pair into a dictionary of tuples """
  if _is_compound_key(k):
    return {_tupleize_compound_key(k): _tupleize_compound_value(v)}
  else:
    return {k: v}


def _tupleize_compound_key(k: str) -> List[str]:
  """ converts a JSON-input compound key into a tuple """
  assert _is_compound_key(k), "{} must be a valid compound key".format(k)
  return tuple([x.strip() for x in k.strip('][').split(',')])


def _tupleize_compound_value(
    v: Union[List, bool, str, int, float]) -> Union[List, Tuple]:
  """ list of lists -> list of tuples
      list of primitives -> tuple of primitives
      single primitive -> length-1 tuple of that primitive

  E.g., [[0,1],[3,4]] -> [(0,1),(3,4)]
        [0,1] -> (0,1)
        0 -> (0, )
  """
  if isinstance(v, list):
    if isinstance(v[0], list):
      # v is list of lists
      return [tuple(vi) for vi in v]
    else:
      # v is list of primitives
      return tuple(v)
  else:
    # v is a single primitive (bool, str, int, float)
    return tuple([v])


def _is_compound_key(s: Any) -> bool:
  """ compound key is defined as a string which uses square brackets to enclose
  a comma-separated list, e.g. "[batch_size,learning_rate]" or "[a,b,c]"
  """

  if type(s) is not str or len(s) <= 2:
    return False
  else:
    return s[0] == '[' and s[-1] == ']'


def dict_product(m: Dict[Any, Any]) -> Iterable[Dict[Any, Any]]:
  """Returns a dictionary generated by taking the cartesian product of each
  list-typed value iterable with all others.

  The iterable of dictionaries returned represents every combination of values.

  If any value is NOT a list it will be treated as a singleton list.

  """

  def wrap_v(v):
    return v if isinstance(v, list) else [v]

  ks = m.keys()
  vs = (wrap_v(v) for v in m.values())
  return (dict(zip(ks, x)) for x in it.product(*vs))


def compose(l, r):
  """Returns a function that's the composition of the two supplied functions.

  """

  def inner(*args, **kwargs):
    return l(r(*args, **kwargs))

  return inner


def flipm(table: Dict[Any, Dict[Any, Any]]) -> Dict[Any, Dict[Any, Any]]:
  """Handles shuffles for a particular kind of table."""
  ret = {}
  for k, m in table.items():
    for k2, v in m.items():
      ret.setdefault(k2, {})[k] = v

  return ret


def invertm(table: Dict[Any, Iterable[Any]]) -> Dict[Any, Set[Any]]:
  """Handles shuffles for a particular kind of table."""
  ret = {}
  for k, vs in table.items():
    for v in vs:
      ret.setdefault(v, set()).add(k)

  return ret


def reorderm(table: Dict[Any, Dict[Any, Iterable[Any]]],
             order: Tuple[int, int, int]) -> Dict[Any, Dict[Any, Set[Any]]]:
  """Handles shuffles for a particular kind of table."""
  ret = {}
  for k, m in table.items():
    for k2, vs in m.items():
      for v in vs:
        fields = [k, k2, v]
        innerm = ret.setdefault(fields[order[0]], {})
        acc = innerm.setdefault(fields[order[1]], set())
        acc.add(fields[order[2]])

  return ret


def merge(l: Dict[Any, Any], r: Dict[Any, Any]) -> Dict[Any, Any]:
  """Returns a new dictionary by merging the two supplied dictionaries."""
  ret = l.copy()
  ret.update(r)
  return ret


def dict_by(keys: Set[str], f: Callable[[str], Any]) -> Dict[str, Any]:
  """Returns a dictionary with keys equal to the supplied keyset. Each value is
  the result of applying f to a key in keys.

  """
  return {k: f(k) for k in keys}


def expand_args(items: Dict[str, str]) -> List[str]:
  """Converts the input map into a sequence of k, v pair strings. A None value is
  interpreted to mean that the key is a solo flag; it's evicted from the
  output.

  """
  pairs = [[k, v] if v is not None else [k] for k, v in items.items()]
  return list(it.chain.from_iterable(pairs))


def split_by(items: List[str],
             separator: Optional[str] = None) -> Tuple[List[str], List[str]]:
  """If the separator is present in the list, returns a 2-tuple of

  - the items before the separator,
  - all items after the separator.

  If the separator isn't present, returns a tuple of

  - (the original list, [])

  """
  if separator is None:
    separator = '--'

  try:
    idx = items.index(separator)
    return items[0:idx], items[idx + 1:]
  except ValueError:
    return (items, [])


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


def path_to_module(path_str: str) -> str:
  return path_str.replace(".py", "").replace(os.path.sep, ".")


def module_to_path(module_name: str) -> str:
  """Converts the supplied python module (module names separated by dots) into
  the python file represented by the module name.

  """
  return module_name.replace(".", os.path.sep) + ".py"


def file_exists_in_cwd(path: str) -> bool:
  """Returns True if the current path references a valid file in the current
  directory, False otherwise.

  """
  return os.path.isfile(os.path.join(os.getcwd(), path))


def extract_root_directory(path: str) -> str:
  """Returns the root directory of the supplied path."""
  items = path.split(os.path.sep)
  return "." if len(items) == 1 else items[0]


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


def validated_package(path: str) -> Package:
  """similar to generate_package but runs argparse validation on packages that
  don't actually exist in the filesystem.

  """
  p = generate_package(path)

  if not os.path.isdir(p.package_path):
    raise argparse.ArgumentTypeError(
        """Directory '{}' doesn't exist in directory. Code must be
nested in a folder that exists in the current directory.""".format(
            p.package_path))

  filename = p.script_path
  if not file_exists_in_cwd(filename):
    raise argparse.ArgumentTypeError(
        """File '{}' doesn't exist locally as a script or python module; code
must live inside the current directory.""".format(filename))

  return p


def parse_kv_pair(s: str) -> Tuple[str, str]:
  """
    Parse a key, value pair, separated by '='

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"
    """
  items = s.split('=')
  k = items[0].strip()  # Remove whitespace around keys

  if len(items) <= 1:
    raise argparse.ArgumentTypeError(
        "Couldn't parse label '{}' into k=v format.".format(s))

  v = '='.join(items[1:])
  return (k, v)


def _is_key(k: Optional[str]) -> bool:
  """Returns True if the argument is a valid argparse optional arg input, False
  otherwise.

  Strings that start with - or -- are considered valid for now.

  """
  return k is not None and len(k) > 0 and k[0] == "-"


def _truncate(s: str, max_length: int) -> str:
  """Returns the input string s truncated to be at most max_length characters
  long.

  """
  return s if len(s) <= max_length else s[0:max_length]


def _clean_label(s: Optional[str], is_key: bool) -> str:
  """Processes the string into the sanitized format required by AI platform
  labels.

  https://cloud.google.com/ml-engine/docs/resource-labels

  """
  if s is None:
    return ""

  # periods are not allowed by AI Platform labels, but often occur in,
  # e.g., learning rates
  DECIMAL_REPLACEMENT = '_'
  s = s.replace('.', DECIMAL_REPLACEMENT)

  # lowercase, letters, - and _ are valid, so strip the leading dashes, make
  # everything lowercase and then kill any remaining unallowed characters.
  cleaned = re.sub(r'[^a-z0-9_-]', '', s.lower()).lstrip("-")

  # Keys must start with a letter. If is_key is set and the cleaned version
  # starts with something else, append `k`.
  if is_key and cleaned != "" and not cleaned[0].isalpha():
    cleaned = "k" + cleaned

  return _truncate(cleaned, AI_PLATFORM_MAX_LABEL_LENGTH)


def key_label(k: Optional[str]) -> str:
  """converts the argument into a valid label, suitable for submission as a label
  key to Cloud.

  """
  return _clean_label(k, True)


def value_label(v: Optional[str]) -> str:
  """converts the argument into a valid label, suitable for submission as a label
  value to Cloud.

  """
  return _clean_label(v, False)


def n_chunks(items: List[Any], n_groups: int) -> List[List[Any]]:
  """Returns a list of `n_groups` slices of the original list, guaranteed to
  contain all of the original items.

  """
  return [items[i::n_groups] for i in range(n_groups)]


def chunks_below_limit(items: List[Any], limit: int) -> List[List[Any]]:
  """Breaks the input list into a series of chunks guaranteed to be less than"""
  quot, _ = divmod(len(items), limit)
  return n_chunks(items, quot + 1)


def partition(seq: List[str], n: int) -> List[List[str]]:
  """Generate groups of n items from seq by scanning across the sequence and
  taking chunks of n, offset by 1.

  """
  for i in range(0, max(1, len(seq) - n + 1), 1):
    yield seq[i:i + n]


def script_args_to_labels(script_args: Optional[List[str]]) -> Dict[str, str]:
  """Converts the arguments supplied to our scripts into a dictionary usable as
  labels valid for Cloud submission.

  """
  ret = {}

  def process_pair(k, v):
    if _is_key(k):
      clean_k = key_label(k)
      if clean_k != "":
        ret[clean_k] = "" if _is_key(v) else value_label(v)

  if script_args is None or len(script_args) == 0:
    return ret

  elif len(script_args) == 1:
    process_pair(script_args[0], None)

  # Handle the case where the final argument in the list is a boolean flag.
  # This won't get picked up by partition.
  elif len(script_args) > 1:
    for k, v in partition(script_args, 2):
      process_pair(k, v)

    process_pair(script_args[-1], None)

  return ret


def sanitize_labels(
    pairs: Union[Dict[str, str], List[Tuple[str, str]]]) -> Dict[str, str]:
  """Turns a dict, or a list of unsanitized key-value pairs (each represented by
  a tuple) into a dictionary suitable to submit to Cloud as a label dict.

  """
  if isinstance(pairs, dict):
    return sanitize_labels(pairs.items())

  return {key_label(k): value_label(v) for (k, v) in pairs if key_label(k)}


def validated_directory(path: str) -> str:
  """This validates that the supplied directory exists locally.

  """
  if not os.path.isdir(path):
    raise argparse.ArgumentTypeError(
        """Directory '{}' doesn't exist in this directory. Check yourself!""".
        format(path))
  return path


def validated_file(path: str) -> str:
  """This validates that the supplied file exists. Tilde expansion is supported.

  """
  expanded = os.path.expanduser(path)
  if not os.path.isfile(expanded):
    raise argparse.ArgumentTypeError(
        """File '{}' isn't a valid file on your system. Try again!""".format(
            path))
  return path


class TqdmFile(object):
  """Dummy file-like that will write to tqdm"""
  file = None
  prefix = _term_move_up() + '\r'

  def __init__(self, file):
    self.file = file
    self._carriage_pending = False

  def write(self, line):
    if self._carriage_pending:
      line = self.prefix + line
      self._carriage_pending = False

    if line.endswith('\r'):
      self._carriage_pending = True
      line = line[:-1] + '\n'

    tqdm.tqdm.write(line, file=self.file, end='')

  def flush(self):
    return getattr(self.file, "flush", lambda: None)()

  def isatty(self):
    return getattr(self.file, "isatty", lambda: False)()

  def close(self):
    return getattr(self.file, "close", lambda: None)()


def config_logging():
  """Overrides logging to go through TQDM.

  TODO use this call to kill then restore:
  https://github.com/tqdm/tqdm#redirecting-writing

  """
  h = logging.get_absl_handler()
  old = h.python_handler
  h._python_handler = logging.PythonHandler(stream=TqdmFile(sys.stderr))
  logging.use_python_logging()


@contextlib.contextmanager
def tqdm_logging():
  """Overrides logging to go through TQDM.

  https://github.com/tqdm/tqdm#redirecting-writing

  """
  handler = logging.get_absl_handler()
  orig = handler.python_handler

  try:
    handler._python_handler = logging.PythonHandler(stream=TqdmFile(sys.stderr))

    # The changes won't take effect if this hasn't been called. Defensively
    # call it again here.
    logging.use_python_logging()
    yield orig.stream
  except Exception as exc:
    raise exc
  finally:
    handler._python_handler = orig


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
