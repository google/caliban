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

from __future__ import absolute_import, division, print_function

import json
import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, NewType, Optional, Union

from absl import logging
from blessings import Terminal

import caliban.config as c
import caliban.util as u
import caliban.util.fs as ufs

t = Terminal()

DEV_CONTAINER_ROOT = "gcr.io/blueshift-playground/blueshift"
TF_VERSIONS = {"2.2.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR = "/usr/app"
CREDS_DIR = "/.creds"
CONDA_BIN = "/opt/conda/bin/conda"

ImageId = NewType('ImageId', str)
ArgSeq = NewType('ArgSeq', List[str])


class DockerError(Exception):
  """Exception that passes info on a failed Docker command."""

  def __init__(self, message, cmd, ret_code):
    super().__init__(message)
    self.message = message
    self.cmd = cmd
    self.ret_code = ret_code

  @property
  def command(self):
    return " ".join(self.cmd)


class NotebookInstall(Enum):
  """Flag to decide what to do ."""
  none = 'none'
  lab = 'lab'
  jupyter = 'jupyter'

  def __str__(self) -> str:
    return self.value


class Shell(Enum):
  """Add new shells here and below, in SHELL_DICT."""
  bash = 'bash'
  zsh = 'zsh'

  def __str__(self) -> str:
    return self.value


# Tuple to track the information required to install and execute some custom
# shell into a container.
ShellData = NamedTuple("ShellData", [("executable", str),
                                     ("packages", List[str])])


def apt_install(*packages: str) -> str:
  """Returns a command that will install the supplied list of packages without
  requiring confirmation or any user interaction.
  """
  package_str = ' '.join(packages)
  no_prompt = "DEBIAN_FRONTEND=noninteractive"
  return f"{no_prompt} apt-get install --yes --no-install-recommends {package_str}"


def apt_command(commands: List[str]) -> List[str]:
  """Pre-and-ap-pends the supplied commands with the appropriate in-container and
  cleanup command for aptitude.

  """
  update = ["apt-get update"]
  cleanup = ["apt-get clean", "rm -rf /var/lib/apt/lists/*"]
  return update + commands + cleanup


# Dict linking a particular supported shell to the data required to run and
# install the shell inside a container.
#
# : Dict[Shell, ShellData]
SHELL_DICT = {
    Shell.bash: ShellData("/bin/bash", []),
    Shell.zsh: ShellData("/bin/zsh", ["zsh"])
}


def default_shell() -> Shell:
  """Returns the shell to load into the container. Defaults to Shell.bash, but if
  the user's SHELL variable refers to a supported sub-shell, returns that
  instead.

  """
  ret = Shell.bash

  if "zsh" in os.environ.get("SHELL"):
    ret = Shell.zsh

  return ret


def adc_location(home_dir: Optional[str] = None) -> str:
  """Returns the location for application default credentials, INSIDE the
  container (so, hardcoded unix separators), given the supplied home directory.

  """
  if home_dir is None:
    home_dir = Path.home()

  return "{}/.config/gcloud/application_default_credentials.json".format(
      home_dir)


def container_home():
  """Returns the location of the home directory inside the generated
  container.

  """
  return "/home/{}".format(u.current_user())


def tf_base_image(job_mode: c.JobMode, tensorflow_version: str) -> str:
  """Returns the base image to use, depending on whether or not we're using a
  GPU. This is JUST for building our base images for Blueshift; not for
  actually using in a job.

  List of available tags: https://hub.docker.com/r/tensorflow/tensorflow/tags

  """
  if tensorflow_version not in TF_VERSIONS:
    raise Exception("""{} is not a valid tensorflow version.
    Try one of: {}""".format(tensorflow_version, TF_VERSIONS))

  gpu = "-gpu" if c.gpu(job_mode) else ""
  return "tensorflow/tensorflow:{}{}-py3".format(tensorflow_version, gpu)


def base_image_suffix(job_mode: c.JobMode) -> str:
  return "gpu" if c.gpu(job_mode) else "cpu"


def base_image_id(job_mode: c.JobMode) -> str:
  """Returns the default base image for all caliban Dockerfiles."""
  base_suffix = base_image_suffix(job_mode)
  return "{}:{}".format(DEV_CONTAINER_ROOT, base_suffix)


def extras_string(extras: List[str]) -> str:
  """Returns the argument passed to `pip install` to install a project from its
  setup.py and target a specific set of extras_require dependencies.

    Args:
        extras: (potentially empty) list of extra_requires deps.
  """
  ret = "."
  if len(extras) > 0:
    ret += "[{}]".format(','.join(extras))
  return ret


def base_extras(job_mode: c.JobMode, path: str,
                extras: Optional[List[str]]) -> Optional[List[str]]:
  """Returns None if the supplied path doesn't exist (it's assumed it points to a
  setup.py file).

  If the path DOES exist, generates a list of extras to install. gpu or cpu are
  always added to the beginning of the list, depending on the mode.

  """
  ret = None

  if os.path.exists(path):
    base = extras or []
    extra = 'gpu' if c.gpu(job_mode) else 'cpu'
    ret = base if extra in base else [extra] + base

  return ret


def _dependency_entries(workdir: str,
                        user_id: int,
                        user_group: int,
                        requirements_path: Optional[str] = None,
                        conda_env_path: Optional[str] = None,
                        setup_extras: Optional[List[str]] = None) -> str:
  """Returns the Dockerfile entries required to install dependencies from either:

  - a requirements.txt file, path supplied by requirements_path
  - a conda environment.yml file, path supplied by conda_env_path.
  - a setup.py file, if some sequence of dependencies is supplied.

  An empty list for setup_extras means, run `pip install -c .` with no extras.
  None for this argument means do nothing. If a list of strings is supplied,
  they'll be treated as extras dependency sets.
  """
  ret = ""

  if setup_extras is not None:
    ret += f"""
COPY --chown={user_id}:{user_group} setup.py {workdir}
RUN /bin/bash -c "pip install --no-cache-dir {extras_string(setup_extras)}"
"""

  if conda_env_path is not None:
    ret += f"""
COPY --chown={user_id}:{user_group} {conda_env_path} {workdir}
RUN /bin/bash -c "{CONDA_BIN} env update \
    --quiet --name caliban \
    --file {conda_env_path} && \
    {CONDA_BIN} clean -y -q --all"
"""

  if requirements_path is not None:
    ret += f"""
COPY --chown={user_id}:{user_group} {requirements_path} {workdir}
RUN /bin/bash -c "pip install --no-cache-dir -r {requirements_path}"
"""

  return ret


def _package_entries(workdir: str, user_id: int, user_group: int,
                     package: u.Package) -> str:
  """Returns the Dockerfile entries required to:

  - copy a directory of code into a docker container
  - inject an entrypoint that executes a python module inside that directory.

  Python code runs as modules vs scripts so that we can enforce import hygiene
  between files inside a project.

  """
  owner = "{}:{}".format(user_id, user_group)

  arg = package.main_module or package.script_path

  # This needs to use json so that quotes print as double quotes, not single
  # quotes.
  entrypoint_s = json.dumps(package.executable + [arg])

  return """
# Copy project code into the docker container.
COPY --chown={owner} {package_path} {workdir}/{package_path}

# Declare an entrypoint that actually runs the container.
ENTRYPOINT {entrypoint_s}
  """.format_map({
      "owner": owner,
      "package_path": package.package_path,
      "workdir": workdir,
      "entrypoint_s": entrypoint_s
  })


def _service_account_entry(user_id: int, user_group: int, credentials_path: str,
                           docker_credentials_dir: str,
                           write_adc_placeholder: bool):
  """Generates the Dockerfile entries required to transfer a set of Cloud service
  account credentials into the Docker container.

  NOTE the write_adc_placeholder variable is here because the "ctpu" script
  that we use to interact with TPUs has a bug in it, as of 1/21/2020, where the
  script will fail if the application_default_credentials.json file isn't
  present, EVEN THOUGH it properly uses the service account credentials
  registered with gcloud instead of ADC creds.

  If a service account is present, we write a placeholder string to get past
  this problem. This shouldn't matter for anyone else since adc isn't used if a
  service account is present.

  """
  container_creds = "{}/credentials.json".format(docker_credentials_dir)
  ret = """
COPY --chown={user_id}:{user_group} {credentials_path} {container_creds}

# Use the credentials file to activate gcloud, gsutil inside the container.
RUN gcloud auth activate-service-account --key-file={container_creds} && \
  git config --global credential.'https://source.developers.google.com'.helper gcloud.sh

ENV GOOGLE_APPLICATION_CREDENTIALS={container_creds}
""".format_map({
      "user_id": user_id,
      "user_group": user_group,
      "credentials_path": credentials_path,
      "container_creds": container_creds
  })

  if write_adc_placeholder:
    ret += """
RUN echo "placeholder" >> {}
""".format(adc_location(container_home()))

  return ret


def _adc_entry(user_id: int, user_group: int, adc_path: str):
  """Returns the Dockerfile line required to transfer the
  application_default_credentials.json file into the container's home
  directory.

  """
  return """
COPY --chown={user_id}:{user_group} {adc_path} {adc_loc}
    """.format_map({
      "user_id": user_id,
      "user_group": user_group,
      "adc_path": adc_path,
      "adc_loc": adc_location(container_home())
  })


def _credentials_entries(user_id: int,
                         user_group: int,
                         adc_path: Optional[str],
                         credentials_path: Optional[str],
                         docker_credentials_dir: Optional[str] = None) -> str:
  """Returns the Dockerfile entries necessary to copy a user's Cloud credentials
  into the Docker container.

  - adc_path is the relative path inside the current directory to an
    application_default_credentials.json file containing... well, you get it.
  - credentials_path is the relative path inside the current directory to a
    JSON credentials file.
  - docker_credentials_dir is the relative path inside the docker container
    where the JSON file will be copied on build.

  """
  if docker_credentials_dir is None:
    docker_credentials_dir = CREDS_DIR

  ret = ""
  if credentials_path is not None:
    ret += _service_account_entry(user_id,
                                  user_group,
                                  credentials_path,
                                  docker_credentials_dir,
                                  write_adc_placeholder=adc_path is None)

  if adc_path is not None:
    ret += _adc_entry(user_id, user_group, adc_path)

  return ret


def _notebook_entries(lab: bool = False, version: Optional[str] = None) -> str:
  """Returns the Dockerfile entries necessary to install Jupyter{lab}.

  Optionally takes a version string.

  """
  version_suffix = ""

  if version is not None:
    version_suffix = "=={}".format(version)

  library = "jupyterlab" if lab else "jupyter"

  return """
RUN pip install {}{}
""".format(library, version_suffix)


def _custom_packages(
    user_id: int,
    user_group: int,
    packages: Optional[List[str]] = None,
    shell: Optional[Shell] = None,
) -> str:
  """Returns the Dockerfile entries necessary to install custom dependencies for
  the supplied shell and sequence of aptitude packages.

  """
  if packages is None:
    packages = []

  if shell is None:
    shell = Shell.bash

  ret = ""

  to_install = sorted(packages + SHELL_DICT[shell].packages)

  if len(to_install) != 0:
    commands = apt_command([apt_install(*to_install)])
    ret = """
USER root

RUN {commands}

USER {user_id}:{user_group}
""".format_map({
        "commands": " && ".join(commands),
        "user_id": user_id,
        "user_group": user_group
    })

  return ret


def _copy_dir_entry(workdir: str, user_id: int, user_group: int,
                    dirname: str) -> str:
  """Returns the Dockerfile entry necessary to copy a single extra subdirectory
  from the current directory into a docker container during build.

  """
  owner = "{}:{}".format(user_id, user_group)
  return """# Copy {dirname} into the Docker container.
COPY --chown={owner} {dirname} {workdir}/{dirname}
""".format_map({
      "owner": owner,
      "workdir": workdir,
      "dirname": dirname
  })


def _extra_dir_entries(workdir: str, user_id: int, user_group: int,
                       extra_dirs: List[str]) -> str:
  """Returns the Dockerfile entries necessary to copy all directories in the
  extra_dirs list into a docker container during build.

  """
  ret = ""
  for d in extra_dirs:
    ret += "\n{}".format(_copy_dir_entry(workdir, user_id, user_group, d))
  return ret


def _dockerfile_template(
    job_mode: c.JobMode,
    workdir: Optional[str] = None,
    package: Optional[Union[List, u.Package]] = None,
    requirements_path: Optional[str] = None,
    conda_env_path: Optional[str] = None,
    setup_extras: Optional[List[str]] = None,
    adc_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
    jupyter_version: Optional[str] = None,
    inject_notebook: NotebookInstall = NotebookInstall.none,
    shell: Optional[Shell] = None,
    extra_dirs: Optional[List[str]] = None,
    caliban_config: Optional[Dict[str, Any]] = None) -> str:
  """Returns a Dockerfile that builds on a local CPU or GPU base image (depending
  on the value of job_mode) to create a container that:

  - installs any dependency specified in a requirements.txt file living at
    requirements_path, a conda environment at conda_env_path, or any
    dependencies in a setup.py file, including extra dependencies, if
    setup_extras isn't None
  - injects gcloud credentials into the container, so Cloud interaction works
    just like it does locally
  - potentially installs a custom shell, or jupyterlab for notebook support
  - copies all source needed by the main module specified by package, and
    potentially injects an entrypoint that, on run, will run that main module

  Most functions that call _dockerfile_template pass along any kwargs that they
  receive. It should be enough to add kwargs here, then rely on that mechanism
  to pass them along, vs adding kwargs all the way down the call chain.
  """
  uid = os.getuid()
  gid = os.getgid()
  username = u.current_user()

  if isinstance(package, list):
    package = u.Package(*package)

  if workdir is None:
    workdir = DEFAULT_WORKDIR

  base_image = c.base_image(caliban_config, job_mode) or base_image_id(job_mode)

  dockerfile = """
FROM {base_image}

# Create the same group we're using on the host machine.
RUN [ $(getent group {gid}) ] || groupadd --gid {gid} {gid}

# Create the user by name. --no-log-init guards against a crash with large user
# IDs.
RUN useradd --no-log-init --no-create-home -u {uid} -g {gid} --shell /bin/bash {username}

# The directory is created by root. This sets permissions so that any user can
# access the folder.
RUN mkdir -m 777 {workdir} {creds_dir} {c_home}

ENV HOME={c_home}

WORKDIR {workdir}

USER {uid}:{gid}
""".format_map({
      "base_image": base_image,
      "username": username,
      "uid": uid,
      "gid": gid,
      "workdir": workdir,
      "c_home": container_home(),
      "creds_dir": CREDS_DIR
  })
  dockerfile += _credentials_entries(uid,
                                     gid,
                                     adc_path=adc_path,
                                     credentials_path=credentials_path)

  dockerfile += _dependency_entries(workdir,
                                    uid,
                                    gid,
                                    requirements_path=requirements_path,
                                    conda_env_path=conda_env_path,
                                    setup_extras=setup_extras)

  if inject_notebook.value != 'none':
    install_lab = inject_notebook == NotebookInstall.lab
    dockerfile += _notebook_entries(lab=install_lab, version=jupyter_version)

  if extra_dirs is not None:
    dockerfile += _extra_dir_entries(workdir, uid, gid, extra_dirs)

  dockerfile += _custom_packages(uid,
                                 gid,
                                 packages=c.apt_packages(
                                     caliban_config, job_mode),
                                 shell=shell)

  if package is not None:
    # The actual entrypoint and final copied code.
    dockerfile += _package_entries(workdir, uid, gid, package)

  return dockerfile


def docker_image_id(output: str) -> ImageId:
  """Accepts a string containing the output of a successful `docker build`
  command and parses the Docker image ID from the stream.

  NOTE this is probably quite brittle! I can imagine this breaking quite easily
  on a Docker upgrade.

  """
  return ImageId(output.splitlines()[-1].split()[-1])


def build_image(job_mode: c.JobMode,
                build_path: str,
                credentials_path: Optional[str] = None,
                adc_path: Optional[str] = None,
                no_cache: bool = False,
                **kwargs) -> str:
  """Builds a Docker image by generating a Dockerfile and passing it to `docker
  build` via stdin. All output from the `docker build` process prints to
  stdout.

  Returns the image ID of the new docker container; if the command fails,
  throws on error with information about the command and any issues that caused
  the problem.

  """
  with ufs.TempCopy(credentials_path,
                    tmp_name=".caliban_default_creds.json") as creds:
    with ufs.TempCopy(adc_path, tmp_name=".caliban_adc_creds.json") as adc:
      cache_args = ["--no-cache"] if no_cache else []
      cmd = ["docker", "build"] + cache_args + ["--rm", "-f-", build_path]

      dockerfile = _dockerfile_template(job_mode,
                                        credentials_path=creds,
                                        adc_path=adc,
                                        **kwargs)

      joined_cmd = " ".join(cmd)
      logging.info("Running command: {}".format(joined_cmd))

      try:
        output, ret_code = ufs.capture_stdout(cmd, input_str=dockerfile)
        if ret_code == 0:
          return docker_image_id(output)
        else:
          error_msg = "Docker failed with error code {}.".format(ret_code)
          raise DockerError(error_msg, cmd, ret_code)

      except subprocess.CalledProcessError as e:
        logging.error(e.output)
        logging.error(e.stderr)
