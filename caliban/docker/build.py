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
import caliban.util.metrics as um

t = Terminal()

DEV_CONTAINER_ROOT = "gcr.io/blueshift-playground/blueshift"
DEFAULT_GPU_TAG = "gpu-ubuntu1804-py37-cuda101"
DEFAULT_CPU_TAG = "cpu-ubuntu1804-py37"
TF_VERSIONS = {"2.2.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR = "/usr/app"
CREDS_DIR = "/.creds"
RESOURCE_DIR = "/.resources"
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


def copy_command(user_id: int,
                 user_group: int,
                 from_path: str,
                 to_path: str,
                 comment: Optional[str] = None) -> str:
  """Generates a Dockerfile entry that will copy the file at the directory-local
  from_path into the container at to_path.

  If you supply a relative path, Docker will copy the file into the current
  working directory, where it will be overwritten in any interactive mode. We
  recommend using an absolute path!

  """
  cmd = f"COPY --chown={user_id}:{user_group} {from_path} {to_path}\n"

  if comment is not None:
    comment_s = "\n# ".join(comment.split("\n"))
    return f"# {comment_s}\n{cmd}"

  return cmd


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
  return DEFAULT_GPU_TAG if c.gpu(job_mode) else DEFAULT_CPU_TAG


def base_image_id(job_mode: c.JobMode) -> str:
  """Returns the default base image for all caliban Dockerfiles."""
  base_suffix = base_image_suffix(job_mode)
  return f"{DEV_CONTAINER_ROOT}:{base_suffix}"


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

  def copy(from_path, to_path):
    return copy_command(user_id, user_group, from_path, to_path)

  if setup_extras is not None:
    ret += f"""
{copy("setup.py", workdir)}
RUN /bin/bash -c "pip install --no-cache-dir {extras_string(setup_extras)}"
"""

  if conda_env_path is not None:
    ret += f"""
{copy(conda_env_path, workdir)}
RUN /bin/bash -c "{CONDA_BIN} env update \
    --quiet --name caliban \
    --file {conda_env_path} && \
    {CONDA_BIN} clean -y -q --all"
"""

  if requirements_path is not None:
    ret += f"""
{copy(requirements_path, workdir)}
RUN /bin/bash -c "pip install --no-cache-dir -r {requirements_path}"
"""

  return ret


def _cloud_sql_proxy_entry(
    user_id: int,
    user_group: int,
    caliban_config: Optional[Dict[str, Any]] = None,
) -> str:
  """returns dockerfile entry to fetch cloud_sql_proxy, installing in /usr/bin.

  Args:
  user_id: id of non-root user
  user_group: id of non-root group for user
  caliban_config: dictionary of caliban configuration options

  Returns:
  string with Dockerfile directives to install cloud_sql_proxy as root
  and reset the user to the specified user_id:user_group.

  """
  caliban_config = caliban_config or {}
  mlflow_cfg = caliban_config.get('mlflow_config')

  if mlflow_cfg is None:
    return ""

  return f"""
USER root

RUN wget \
  -q https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 \
  -O /usr/bin/cloud_sql_proxy \
  && chmod 755 /usr/bin/cloud_sql_proxy

USER {user_id}:{user_group}
"""


def _generate_entrypoint(executable: str) -> str:
  """generates dockerfile entry to set the container entrypoint.

  Args:
  executable: string of main executable

  Returns:
  string with Dockerfile directives to set ENTRYPOINT

  """
  launcher_cmd = json.dumps([
      'python',
      os.path.join(RESOURCE_DIR, um.LAUNCHER_SCRIPT), '--caliban_command',
      executable
  ])

  return f"""
ENTRYPOINT {launcher_cmd}
"""


def _package_entries(
    workdir: str,
    user_id: int,
    user_group: int,
    package: u.Package,
    caliban_config: Optional[Dict[str, Any]] = None,
) -> str:
  """Returns the Dockerfile entries required to:

  - copy a directory of code into a docker container
  - inject an entrypoint that executes a python module inside that directory.

  Python code runs as modules vs scripts so that we can enforce import hygiene
  between files inside a project.

  """
  caliban_config = caliban_config or {}

  arg = package.main_module or package.script_path
  package_path = package.package_path

  sql_proxy_code = _cloud_sql_proxy_entry(user_id,
                                          user_group,
                                          caliban_config=caliban_config)

  copy_code = copy_command(
      user_id,
      user_group,
      package_path,
      f"{workdir}/{package_path}",
      comment="Copy project code into the docker container.")

  # This needs to use json so that quotes print as double quotes, not single
  # quotes.
  executable_s = json.dumps(package.executable + [arg])
  entrypoint_code = _generate_entrypoint(executable_s)

  return f"""
  {sql_proxy_code}

  {copy_code}

  {entrypoint_code}
"""


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
  container_creds = f"{docker_credentials_dir}/credentials.json"
  ret = f"""
{copy_command(user_id, user_group, credentials_path, container_creds)}

# Use the credentials file to activate gcloud, gsutil inside the container.
RUN gcloud auth activate-service-account --key-file={container_creds} && \
  git config --global credential.'https://source.developers.google.com'.helper gcloud.sh

ENV GOOGLE_APPLICATION_CREDENTIALS={container_creds}
"""

  if write_adc_placeholder:
    ret += f"""
RUN echo "placeholder" >> {adc_location(container_home())}
"""

  return ret


def _adc_entry(user_id: int, user_group: int, adc_path: str):
  """Returns the Dockerfile line required to transfer the
  application_default_credentials.json file into the container's home
  directory.

  """
  return copy_command(user_id, user_group, adc_path,
                      adc_location(container_home()))


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
  return copy_command(user_id,
                      user_group,
                      dirname,
                      f"{workdir}/{dirname}",
                      comment=f"Copy {dirname} into the Docker container.")


def _extra_dir_entries(workdir: str,
                       user_id: int,
                       user_group: int,
                       extra_dirs: Optional[List[str]] = None) -> str:
  """Returns the Dockerfile entries necessary to copy all directories in the
  extra_dirs list into a docker container during build.

  """
  if extra_dirs is None:
    return ""

  def copy(d):
    return _copy_dir_entry(workdir, user_id, user_group, d)

  return "\n\n".join(map(copy, extra_dirs)) + "\n"


def _resource_entries(uid: int,
                      gid: int,
                      resource_files: Optional[List[str]] = None,
                      resource_dir: str = RESOURCE_DIR) -> str:
  """Returns Dockerfile entries necessary to copy miscellaneous resource files
  into container. Usually these files are staged in the working directory, so
  that Docker's build context can access them.

  Args:
  uid: user id in container for files
  gid: user group id in container for files
  resource_files: list of files to copy
  resource_dir: destination for resource files


  Returns:
  a string to append to a Dockerfile containing COPY commands that will copy
  those resources into a built container.

  """
  if resource_files is None:
    return ""

  def copy(path):
    return copy_command(uid, gid, path, resource_dir)

  return "\n\n".join(map(copy, resource_files)) + "\n"


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
    resource_files: Optional[List[str]] = None,
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
  c_home = container_home()

  dockerfile = f"""
FROM {base_image}

# Create the same group we're using on the host machine.
RUN [ $(getent group {gid}) ] || groupadd --gid {gid} {gid}

# Create the user by name. --no-log-init guards against a crash with large user
# IDs.
RUN useradd --no-log-init --no-create-home -u {uid} -g {gid} --shell /bin/bash {username}

# The directory is created by root. This sets permissions so that any user can
# access the folder.
RUN mkdir -m 777 {workdir} {CREDS_DIR} {RESOURCE_DIR} {c_home}

ENV HOME={c_home}

WORKDIR {workdir}

USER {uid}:{gid}
"""
  dockerfile += _credentials_entries(uid,
                                     gid,
                                     adc_path=adc_path,
                                     credentials_path=credentials_path)

  dockerfile += _custom_packages(uid,
                                 gid,
                                 packages=c.apt_packages(
                                     caliban_config, job_mode),
                                 shell=shell)

  dockerfile += _dependency_entries(workdir,
                                    uid,
                                    gid,
                                    requirements_path=requirements_path,
                                    conda_env_path=conda_env_path,
                                    setup_extras=setup_extras)

  if inject_notebook.value != 'none':
    install_lab = inject_notebook == NotebookInstall.lab
    dockerfile += _notebook_entries(lab=install_lab, version=jupyter_version)

  dockerfile += _extra_dir_entries(workdir, uid, gid, extra_dirs)

  dockerfile += _resource_entries(uid, gid, resource_files)

  if package is not None:
    # The actual entrypoint and final copied code.
    dockerfile += _package_entries(workdir, uid, gid, package, caliban_config)

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
  caliban_config = kwargs.get('caliban_config', {})

  # Paths for resource files.
  sql_proxy_path = um.cloud_sql_proxy_path()
  launcher_path = um.launcher_path()

  with ufs.TempCopy({
      credentials_path: ".caliban_default_creds.json",
      adc_path: ".caliban_adc_creds.json",
      sql_proxy_path: um.CLOUD_SQL_WRAPPER_SCRIPT,
      launcher_path: um.LAUNCHER_SCRIPT,
  }) as creds:

    # generate our launcher configuration file
    with um.launcher_config_file(
        path='.', caliban_config=caliban_config) as launcher_config:

      cache_args = ["--no-cache"] if no_cache else []
      cmd = ["docker", "build"] + cache_args + ["--rm", "-f-", build_path]

      dockerfile = _dockerfile_template(
          job_mode,
          credentials_path=creds.get(credentials_path),
          adc_path=creds.get(adc_path),
          resource_files=[
              creds.get(sql_proxy_path),
              creds.get(launcher_path),
              launcher_config,
          ],
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
