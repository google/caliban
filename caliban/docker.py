"""Functions required to interact with Docker to build and run images, shells
and notebooks in a Docker environment.

"""

from __future__ import absolute_import, division, print_function

import json
import os
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import (Callable, Dict, Iterable, List, NamedTuple, NewType,
                    Optional, Set)

import tqdm
from absl import logging
from blessings import Terminal

import caliban.config as c
import caliban.util as u

t = Terminal()

DEV_CONTAINER_ROOT: str = "gcr.io/blueshift-playground/blueshift"
TF_VERSIONS: Set[str] = {"2.0.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR: str = "/usr/app"
CREDS_DIR: str = "/.creds"

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


class Shell(Enum):
  """Add new shells here and below, in SHELL_DICT."""
  bash = 'bash'
  zsh = 'zsh'

  def __str__(self):
    return self.value


class ShellData(NamedTuple):
  """Tuple to track the information required to install and execute some custom
  shell into a container.

  """
  executable: str
  install_cmds: List[str]


def apt_install(*packages: str) -> str:
  """Returns a command that will install the supplied list of packages without
  requiring confirmation or any user interaction.

  """
  package_str = ' '.join(packages)
  return f"apt-get install --yes --no-install-recommends {package_str}"


def apt_command(commands: List[str]) -> List[str]:
  """Pre-and-ap-pends the supplied commands with the appropriate in-container and
  cleanup command for aptitude.

  """
  update = ["apt-get update"]
  cleanup = ["rm -rf /var/lib/apt/lists/*"]
  return update + commands + cleanup


# Dict linking a particular supported shell to the data required to run and
# install the shell inside a container.
SHELL_DICT: Dict[Shell, ShellData] = {
    Shell.bash: ShellData("/bin/bash", []),
    Shell.zsh: ShellData("/bin/zsh", apt_command([apt_install("zsh")]))
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

  return f"{home_dir}/.config/gcloud/application_default_credentials.json"


def container_home():
  """Returns the location of the home directory inside the generated
  container.

  """
  return f"/home/{u.current_user()}"


def tf_base_image(job_mode: c.JobMode, tensorflow_version: str) -> str:
  """Returns the base image to use, depending on whether or not we're using a
  GPU. This is JUST for building our base images for Blueshift; not for
  actually using in a job.

  List of available tags: https://hub.docker.com/r/tensorflow/tensorflow/tags

  """
  if tensorflow_version not in TF_VERSIONS:
    raise Exception(f"""{tensorflow_version} is not a valid tensorflow version.
    Try one of: {TF_VERSIONS}""")

  gpu = "-gpu" if c.gpu(job_mode) else ""
  return f"tensorflow/tensorflow:{tensorflow_version}{gpu}-py3"


def base_image_suffix(job_mode: c.JobMode) -> str:
  return "gpu" if c.gpu(job_mode) else "cpu"


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
    ret += f"[{','.join(extras)}]"
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
                        setup_extras: Optional[List[str]] = None) -> str:
  """Returns the Dockerfile entries required to install dependencies from either:

  - a requirements.txt file, path supplied by requirements_path
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
  owner = f"{user_id}:{user_group}"

  arg = package.main_module or package.script_path

  # This needs to use json so that quotes print as double quotes, not single
  # quotes.
  entrypoint_s = json.dumps(package.executable + [arg])

  return f"""
# Copy project code into the docker container.
COPY --chown={owner} {package.package_path} {workdir}/{package.package_path}

# Declare an entrypoint that actually runs the container.
ENTRYPOINT {entrypoint_s}
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
COPY --chown={user_id}:{user_group} {credentials_path} {container_creds}

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
  return f"""
COPY --chown={user_id}:{user_group} {adc_path} {adc_location(container_home())}
    """


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


def _notebook_entries(version: Optional[str] = None) -> str:
  """Returns the Dockerfile entries necessary to install Jupyterlab.

  Optionally takes a version string.

  """
  version_suffix = ""

  if version is not None:
    version_suffix = f"=={version}"

  return f"""
RUN pip install jupyterlab{version_suffix}
"""


def _custom_shell_entries(user_id: int,
                          user_group: int,
                          shell: Optional[Shell] = None) -> str:
  """Returns the Dockerfile entries necessary to install the dependencies for the
  supplied shell.

  """
  if shell is None:
    shell = Shell.bash

  ret = ""

  commands = SHELL_DICT[shell].install_cmds
  if len(commands) != 0:
    ret = f"""
USER root

RUN {" && ".join(commands)}

USER {user_id}:{user_group}
"""

  return ret


def _copy_dir_entry(workdir: str, user_id: int, user_group: int,
                    dirname: str) -> str:
  """Returns the Dockerfile entry necessary to copy a single extra subdirectory
  from the current directory into a docker container during build.

  """
  owner = f"{user_id}:{user_group}"
  return f"""# Copy {dirname} into the Docker container.
COPY --chown={owner} {dirname} {workdir}/{dirname}
"""


def _extra_dir_entries(workdir: str, user_id: int, user_group: int,
                       extra_dirs: List[str]) -> str:
  """Returns the Dockerfile entries necessary to copy all directories in the
  extra_dirs list into a docker container during build.

  """
  ret = ""
  for d in extra_dirs:
    ret += f"\n{_copy_dir_entry(workdir, user_id, user_group, d)}"
  return ret


def _dockerfile_template(job_mode: c.JobMode,
                         workdir: Optional[str] = None,
                         base_image_fn: Optional[Callable[[c.JobMode],
                                                          str]] = None,
                         package: Optional[u.Package] = None,
                         requirements_path: Optional[str] = None,
                         setup_extras: Optional[List[str]] = None,
                         adc_path: Optional[str] = None,
                         credentials_path: Optional[str] = None,
                         jupyter_version: Optional[str] = None,
                         inject_notebook: bool = False,
                         shell: Optional[Shell] = None,
                         extra_dirs: Optional[List[str]] = None) -> str:
  """Returns a Dockerfile that builds on a local CPU or GPU base image (depending
  on the value of job_mode) to create a container that:

  - installs any dependency specified in a requirements.txt file living at
    requirements_path, or any dependencies in a setup.py file, including extra
    dependencies, if setup_extras isn't None
  - injects gcloud credentials into the container, so Cloud interaction works
    just like it does locally
  - potentially installs a custom shell, or jupyterlab for notebook support
  - copies all source needed by the main module specified by package, and
    potentially injects an entrypoint that, on run, will run that main module

  Most functions that call _dockerfile_template pass along any kwargs that they
  receive. It should be enough to add kwargs here, then rely on that mechanism
  to pass them along, vs adding kwargs all the way down the call chain.

  Supply a custom base_image_fn (function from job_mode -> image ID) to inject
  more complex Docker commands into the Caliban environments by, for example,
  building your own image on top of the TF base images, then using that.

  """
  uid = os.getuid()
  gid = os.getgid()
  username = u.current_user()

  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if base_image_fn is None:
    base_image_fn = base_image_id

  base_image = base_image_fn(job_mode)

  dockerfile = f"""
FROM {base_image}

# Create the same group we're using on the host machine.
RUN groupadd --gid {gid} {gid}

# Create the user by name.
RUN useradd --no-create-home -u {uid} -g {gid} --shell /bin/bash {username}

# The directory is created by root. This sets permissions so that any user can
# access the folder.
RUN mkdir -m 777 {workdir} {CREDS_DIR} {container_home()}

ENV HOME={container_home()}

WORKDIR {workdir}

USER {uid}:{gid}
"""
  dockerfile += _credentials_entries(uid,
                                     gid,
                                     adc_path=adc_path,
                                     credentials_path=credentials_path)

  dockerfile += _dependency_entries(workdir,
                                    uid,
                                    gid,
                                    requirements_path=requirements_path,
                                    setup_extras=setup_extras)

  if inject_notebook:
    dockerfile += _notebook_entries(version=jupyter_version)

  if extra_dirs is not None:
    dockerfile += _extra_dir_entries(workdir, uid, gid, extra_dirs)

  dockerfile += _custom_shell_entries(uid, gid, shell)

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
  with u.TempCopy(credentials_path,
                  tmp_name=".caliban_default_creds.json") as creds:
    with u.TempCopy(adc_path, tmp_name=".caliban_adc_creds.json") as adc:
      cache_args = ["--no-cache"] if no_cache else []
      cmd = ["docker", "build"] + cache_args + ["--rm", "-f-", os.getcwd()]

      dockerfile = _dockerfile_template(job_mode,
                                        credentials_path=creds,
                                        adc_path=adc,
                                        **kwargs)

      joined_cmd = " ".join(cmd)
      logging.info(f"Running command: {joined_cmd}")

      try:
        output, ret_code = u.capture_stdout(cmd, input_str=dockerfile)
        if ret_code == 0:
          return docker_image_id(output)
        else:
          error_msg = f"Docker failed with error code {ret_code}."
          raise DockerError(error_msg, cmd, ret_code)

      except subprocess.CalledProcessError as e:
        logging.error(e.output)
        logging.error(e.stderr)


def _image_tag_for_project(project_id: str, image_id: str) -> str:
  """Generate the GCR Docker image tag for the supplied pair of project_id and
  image_id.

  This function properly handles "domain scoped projects", where the project ID
  contains a domain name and project ID separated by :
  https://cloud.google.com/container-registry/docs/overview#domain-scoped_projects.

  """
  project_s = project_id.replace(":", "/")
  return f"gcr.io/{project_s}/{image_id}:latest"


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


def _run_cmd(job_mode: c.JobMode,
             run_args: Optional[List[str]] = None) -> List[str]:
  """Returns the sequence of commands for the subprocess run functions required
  to execute `docker run`. in CPU or GPU mode, depending on the value of
  job_mode.

  Keyword args:
  - run_args: list of args to pass to docker run.

  """
  if run_args is None:
    run_args = []

  runtime = ["--runtime", "nvidia"] if c.gpu(job_mode) else []
  return ["docker", "run"] + runtime + ["--ipc", "host"] + run_args


def _home_mount_cmds(enable_home_mount: bool) -> List[str]:
  """Returns the argument needed by Docker to mount a user's local home directory
  into the home directory location inside their container.

  If enable_home_mount is false returns an empty list.

  """
  ret = []
  if enable_home_mount:
    ret = ["-v", f"{Path.home()}:{container_home()}"]
  return ret


def _interactive_opts(workdir: str) -> List[str]:
  """Returns the basic arguments we want to run a docker process locally.

  """
  return [
      "-w", workdir, \
      "-u", f"{os.getuid()}:{os.getgid()}", \
      "-v", f"{os.getcwd()}:{workdir}" \
  ]


def log_arg_instance(args: ArgSeq, i: int) -> ArgSeq:
  """Prints logging as a side effect for the supplied sequence of arguments
  generated from an experiment definition; returns the input args.

  """
  logging.info("")
  logging.info(f"Job {i} - Experiment args: {t.yellow(str(args))}")
  return args


def logged_args(experiments: Iterable[c.Experiment],
                base_args: ArgSeq) -> Iterable[ArgSeq]:
  """Generates an iterable of arguments that should be passed to `docker run` to
  execute the experiments defined by the supplied iterable.

  """
  for i, m in enumerate(experiments, 1):
    args = c.experiment_to_args(m, base_args)
    yield log_arg_instance(args, i)


def execute_dry_run(experiments: Iterable[c.Experiment],
                    base_args: ArgSeq) -> None:
  """Expands the supplied sequence of experiments into sequences of args and logs
  the jobs that WOULD have been executed, had the dry run flag not been
  applied.

  """
  list(logged_args(experiments, base_args))

  logging.info('')
  logging.info(
      t.yellow(f"To build your image and execute these jobs, \
run your command again without {c.DRY_RUN_FLAG}."))
  logging.info('')
  return None


def local_callback(ret_code: int, job_idx: int, script_args: List[str]) -> None:
  """Provides logging feedback for jobs run locally. If the return code is 0,
  logs success; else, logs the failure as an error and logs the script args
  that provided the failure.

  """
  if ret_code == 0:
    logging.info(t.green(f"Job {job_idx} succeeded!"))
  else:
    logging.error(t.red(f"Job {job_idx} failed with return code {ret_code}."))
    logging.error(t.red(f"Failing args for job {job_idx}: {script_args}"))


def execute_experiments(experiments: Iterable[c.Experiment],
                        base_args: List[str], job_mode: c.JobMode,
                        run_args: List[str], image_id: str) -> None:
  """Execute all batches in the supplied generator of batch requests. Results
  aren't returned directly; the callbacks passed to each request when it was
  generated handle any response or exception.

  """
  base_cmd = _run_cmd(job_mode, run_args) + [image_id]

  with u.tqdm_logging() as orig_stream:
    pbar = tqdm.tqdm(logged_args(experiments, base_args),
                     file=orig_stream,
                     total=len(experiments),
                     unit="experiment",
                     desc="Executing")
    for idx, script_args in enumerate(pbar, 1):
      command = base_cmd + script_args
      logging.info(f"Running command: {' '.join(command)}")
      _, ret_code = u.capture_stdout(command, "", u.TqdmFile(sys.stderr))
      local_callback(ret_code, idx, script_args)

  return None


def run_experiments(job_mode: c.JobMode,
                    run_args: Optional[List[str]] = None,
                    script_args: Optional[List[str]] = None,
                    image_id: Optional[str] = None,
                    dry_run: bool = False,
                    experiment_config: Optional[c.ExpConf] = None,
                    **build_image_kwargs) -> None:
  """Builds an image using the supplied **build_image_kwargs and calls `docker
  run` on the resulting image using sensible defaults.

  Keyword args:

  - job_mode: c.JobMode.

  - run_args: extra arguments to supply to `docker run` after our defaults.
  - script_args: extra arguments to supply to the entrypoint. (You can
  - override the default container entrypoint by supplying a new one inside
    run_args.)
  - image_id: ID of the image to run. Supplying this will skip an image build.
  - experiment_config: dict of string to list, boolean, string or int. Any
    lists will trigger a cartesian product out with the rest of the config. A
    job will be executed for every combination of parameters in the experiment
    config.
  - dry_run: if True, no actual jobs will be executed and docker won't
    actually build; logging side effects will show the user what will happen
    without dry_run=True.

  any extra kwargs supplied are passed through to build_image.
  """
  if run_args is None:
    run_args = []

  if script_args is None:
    script_args = []

  if experiment_config is None:
    experiment_config = {}

  if image_id is None:
    if dry_run:
      logging.info("Dry run - skipping actual 'docker build'.")
      image_id = "dry_run_tag"
    else:
      image_id = build_image(job_mode, **build_image_kwargs)

  experiments = c.expand_experiment_config(experiment_config)

  if dry_run:
    return execute_dry_run(experiments, script_args)

  return execute_experiments(experiments, script_args, job_mode, run_args,
                             image_id)


def run(job_mode: c.JobMode,
        run_args: Optional[List[str]] = None,
        script_args: Optional[List[str]] = None,
        image_id: Optional[str] = None,
        **build_image_kwargs) -> None:
  """Builds an image using the supplied **build_image_kwargs and calls `docker
  run` on the resulting image using sensible defaults.
  Keyword args:
  - job_mode: c.JobMode.
  - run_args: extra arguments to supply to `docker run` after our defaults.
  - script_args: extra arguments to supply to the entrypoint. (You can
  - override the default container entrypoint by supplying a new one inside
    run_args.)
  - image_id: ID of the image to run. Supplying this will skip an image build.
  any extra kwargs supplied are passed through to build_image.
  """
  if run_args is None:
    run_args = []

  if script_args is None:
    script_args = []

  if image_id is None:
    image_id = build_image(job_mode, **build_image_kwargs)

  base_cmd = _run_cmd(job_mode, run_args)

  command = base_cmd + [image_id] + script_args

  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)
  return None


def run_interactive(job_mode: c.JobMode,
                    workdir: Optional[str] = None,
                    image_id: Optional[str] = None,
                    run_args: Optional[List[str]] = None,
                    mount_home: Optional[bool] = None,
                    shell: Optional[Shell] = None,
                    entrypoint: Optional[str] = None,
                    entrypoint_args: Optional[List[str]] = None,
                    **build_image_kwargs) -> None:
  """Start a live shell in the terminal, with all dependencies installed and the
  current working directory (and optionally the user's home directory) mounted.

  Keyword args:

  - job_mode: c.JobMode.
  - image_id: ID of the image to run. Supplying this will skip an image build.
  - run_args: extra arguments to supply to `docker run`.
  - mount_home: if true, mounts the user's $HOME directory into the container
    to `/home/$USERNAME`. If False, nothing.
  - shell: name of the shell to install into the container. Also configures the
    entrypoint if that's not supplied.
  - entrypoint: command to run. Defaults to the executable command for the
    supplied shell.
  - entrypoint_args: extra arguments to supply to the entrypoint.

  any extra kwargs supplied are passed through to build_image.

  """
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if run_args is None:
    run_args = []

  if entrypoint_args is None:
    entrypoint_args = []

  if mount_home is None:
    mount_home = True

  if shell is None:
    # Only set a default shell if we're also mounting the home volume.
    # Otherwise a custom shell won't have access to the user's profile.
    shell = default_shell() if mount_home else Shell.bash

  if entrypoint is None:
    entrypoint = SHELL_DICT[shell].executable

  interactive_run_args = _interactive_opts(workdir) + [
      "-it", \
      "--entrypoint", entrypoint
  ] + _home_mount_cmds(mount_home) + run_args

  run(job_mode=job_mode,
      run_args=interactive_run_args,
      script_args=entrypoint_args,
      image_id=image_id,
      shell=shell,
      workdir=workdir,
      **build_image_kwargs)


def run_notebook(job_mode: c.JobMode,
                 port: Optional[int] = None,
                 lab: Optional[bool] = None,
                 version: Optional[bool] = None,
                 run_args: Optional[List[str]] = None,
                 **run_interactive_kwargs) -> None:
  """Start a notebook in the current working directory; the process will run
  inside of a Docker container that's identical to the environment available to
  Cloud jobs that are submitted by `caliban cloud`, or local jobs run with
  `caliban run.`

  if you pass mount_home=True your jupyter settings will persist across calls.

  Keyword args:

  - port: the port to pass to Jupyter when it boots, useful if you have
    multiple instances running on one machine.
  - lab: if True, starts jupyter lab, else jupyter notebook.
  - version: explicit Jupyter version to install.

  run_interactive_kwargs are all extra arguments taken by run_interactive.

  """

  if port is None:
    port = u.next_free_port(8888)

  if lab is None:
    lab = False

  if run_args is None:
    run_args = []

  jupyter_cmd = "lab" if lab else "notebook"
  jupyter_args = [
    "-m", "jupyter", jupyter_cmd, \
    "--ip=0.0.0.0", \
    f"--port={port}", \
    "--no-browser"
  ]
  docker_args = ["-p", f"{port}:{port}"] + run_args

  run_interactive(job_mode,
                  entrypoint="/opt/venv/bin/python",
                  entrypoint_args=jupyter_args,
                  run_args=docker_args,
                  inject_notebook=True,
                  jupyter_version=version,
                  **run_interactive_kwargs)
