"""Functions required to interact with Docker to build and run images, shells
and notebooks in a Docker environment.

"""

from __future__ import absolute_import, division, print_function

import getpass
import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

from absl import logging

import caliban.util as u

DEV_CONTAINER_ROOT = "gcr.io/blueshift-playground/blueshift"
TF_VERSIONS = {"2.0.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR = "/usr/app"
CREDS_DIR = "/.creds"


def tf_base_image(tensorflow_version: str, use_gpu: bool) -> str:
  """Returns the base image to use, depending on whether or not we're using a
  GPU. This is JUST for building our base images for Blueshift; not for
  actually using in a job.

  List of available tags: https://hub.docker.com/r/tensorflow/tensorflow/tags

  """
  if tensorflow_version not in TF_VERSIONS:
    raise Exception(f"""{tensorflow_version} is not a valid tensorflow version.
    Try one of: {TF_VERSIONS}""")

  gpu = "-gpu" if use_gpu else ""
  return f"tensorflow/tensorflow:{tensorflow_version}{gpu}-py3"


def base_image_suffix(use_gpu: bool) -> str:
  return "gpu" if use_gpu else "cpu"


def base_image_id(use_gpu: bool) -> str:
  """Returns the default base image for all caliban Dockerfiles."""
  return "{}:{}".format(DEV_CONTAINER_ROOT, base_image_suffix(use_gpu))


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


def default_shell() -> str:
  """Returns the shell command of the current system. Defaults to bash"""
  return os.environ.get("SHELL", "/bin/bash")


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
RUN /bin/bash -c "pip install {extras_string(setup_extras)}"
"""

  if requirements_path is not None:
    ret += f"""
COPY --chown={user_id}:{user_group} {requirements_path} {workdir}
RUN /bin/bash -c "pip install -r {requirements_path}"
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
  return f"""
# Copy project code into the docker container.
COPY --chown={owner} {package.package_path} {workdir}/{package.package_path}

# Declare an entrypoint that actually runs the container.
ENTRYPOINT ["python", "-m", "{package.main_module}"]
  """


def _credentials_entries(credentials_path: str,
                         user_id: int,
                         user_group: int,
                         docker_credentials_dir: Optional[str] = None) -> str:
  """Returns the Dockerfile entries necessary to copy a user's Cloud credentials
into the Docker container.

  - credentials_path is the relative path inside the current directory to a
    JSON credentials file.
  - docker_credentials_dir is the relative path inside the docker container
    where the JSON file will be copied on build.

  """
  if docker_credentials_dir is None:
    docker_credentials_dir = CREDS_DIR

  container_creds = f"{docker_credentials_dir}/credentials.json"

  return f"""
COPY --chown={user_id}:{user_group} {credentials_path} {container_creds}

# Use the credentials file to activate gcloud, gsutil inside the container.
RUN gcloud auth activate-service-account --key-file={container_creds}

ENV GOOGLE_APPLICATION_CREDENTIALS={container_creds}
"""


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


def _custom_shell_entries(shell_cmd: Optional[str], user_id: int,
                          user_group: int) -> str:
  """Returns the Dockerfile entries necessary to install the dependencies for the
  shell referenced by the supplied shell_cmd.

  """
  ret = ""
  if shell_cmd is not None:
    if shell_cmd == "/bin/zsh":
      ret = f"""
USER root

RUN apt-get install -y zsh

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


def _dockerfile_template(workdir: str,
                         use_gpu: bool,
                         base_image_fn: Optional[Callable[[bool], str]] = None,
                         package: Optional[u.Package] = None,
                         requirements_path: Optional[str] = None,
                         setup_extras: Optional[List[str]] = None,
                         credentials_path: Optional[str] = None,
                         jupyter_version: Optional[str] = None,
                         inject_notebook: bool = False,
                         shell_cmd: Optional[str] = None,
                         extra_dirs: Optional[List[str]] = None) -> str:
  """Returns a Dockerfile that builds on a local CPU or GPU base image (depending
on the value of use_gpu) to create a container that:

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

  Supply a custom base_image_fn (function from use_gpu -> image ID) to inject
  more complex Docker commands into the Caliban environments by, for example,
  building your own image on top of the TF base images, then using that.

  """
  uid = os.getuid()
  gid = os.getgid()
  username = getpass.getuser()

  if base_image_fn is None:
    base_image_fn = base_image_id

  base_image = base_image_fn(use_gpu)

  dockerfile = f"""
FROM {base_image}

# Create the same group we're using on the host machine.
RUN groupadd --gid {gid} {gid}

# Create the user by name.
RUN useradd --no-create-home -u {uid} -g {gid} --shell /bin/bash {username}

# The directory is created by root. This sets permissions so that any user can
# access the folder.
RUN mkdir -m 777 {workdir} {CREDS_DIR} /home/{username}

ENV HOME=/home/{username}

WORKDIR {workdir}

USER {uid}:{gid}
"""
  dockerfile += _dependency_entries(workdir,
                                    uid,
                                    gid,
                                    requirements_path=requirements_path,
                                    setup_extras=setup_extras)

  if inject_notebook:
    dockerfile += _notebook_entries(version=jupyter_version)

  if credentials_path is not None:
    dockerfile += _credentials_entries(credentials_path, uid, gid)

  if extra_dirs is not None:
    dockerfile += _extra_dir_entries(workdir, uid, gid, extra_dirs)

  if package is not None:
    dockerfile += _package_entries(workdir, uid, gid, package)

  dockerfile += _custom_shell_entries(shell_cmd, uid, gid)

  return dockerfile


def docker_image_id(output: str) -> str:
  """Accepts a string containing the output of a successful `docker build`
  command and parses the Docker image ID from the stream.

  NOTE this is probably quite brittle! I can imagine this breaking quite easily
  on a Docker upgrade.

  """
  return output.splitlines()[-1].split()[-1]


def build_image(use_gpu: bool,
                workdir: Optional[str] = None,
                credentials_path: Optional[str] = None,
                **kwargs) -> str:
  """Builds a Docker image by generating a Dockerfile and passing it to `docker
  build` via stdin. All output from the `docker build` process prints to stdout.

  Returns the image ID of the new docker container; throws on error.

  TODO better error printing if the build fails.

  """
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  with u.TempCopy(credentials_path) as cred_path:
    cmd = ["docker", "build", "--rm", "-f-", os.getcwd()]
    dockerfile = _dockerfile_template(workdir,
                                      use_gpu,
                                      credentials_path=cred_path,
                                      **kwargs)

    logging.info(f"Running command: {' '.join(cmd)}")

    try:
      output = u.capture_stdout(cmd, input_str=dockerfile)
      return docker_image_id(output)

    except subprocess.CalledProcessError as e:
      logging.error(e.output)
      logging.error(e.stderr)


def push_uuid_tag(project_id: str, image_id: str) -> str:
  """Takes a base image and tags it for upload, then pushes it to a remote Google
  Cloud repository.

  Returns the tag on a successful push.

  TODO should this just check first before attempting to push if the image
  exists? Immutable names means that if the has is up there, we're done.
  Potentially use docker-py for this.

  """
  image_tag = f"gcr.io/{project_id}/{image_id}:latest"
  subprocess.run(["docker", "tag", image_id, image_tag], check=True)
  subprocess.run(["docker", "push", image_tag], check=True)
  return image_tag


def _run_cmd(use_gpu: bool) -> List[str]:
  """Returns the sequence of commands for the subprocess run functions required
to execute `docker run`. in CPU or GPU mode, depending on the value of
use_gpu.

  """
  runtime = ["--runtime", "nvidia"] if use_gpu else []
  return ["docker", "run"] + runtime


def _home_mount_cmds(enable_home_mount: bool) -> List[str]:
  """Returns the argument needed by Docker to mount a user's local home directory
  into the home directory location inside their container.

  If enable_home_mount is false returns an empty list.

  """
  ret = []
  if enable_home_mount:
    ret = ["-v", f"{Path.home()}:/home/{getpass.getuser()}"]
  return ret


def _interactive_opts(workdir: str,
                      kvs: Optional[Dict[str, str]] = None) -> Dict[str, str]:
  """Returns the basic arguments we want to run a docker process locally.
  """
  if kvs is None:
    kvs = {}

  base = {
      "-w": workdir,
      "-u": "{}:{}".format(os.getuid(), os.getgid()),
      "-v": "{}:{}".format(os.getcwd(), workdir)
  }
  base.update(kvs)
  return base


def run_interactive(use_gpu: bool,
                    workdir: Optional[str] = None,
                    mount_home: Optional[bool] = None,
                    run_options: Optional[Dict[str, str]] = None,
                    entrypoint_args: Optional[List[str]] = None,
                    shell_cmd: Optional[str] = None,
                    entrypoint: Optional[str] = None,
                    image_id: Optional[str] = None,
                    **kwargs) -> None:
  """Start a live shell in the terminal, with all dependencies installed and the
current working directory (and optionally the user's home directory) mounted.

  Keyword args:

  - use_gpu: True for GPU mode, False for CPU.
  - workdir: the in-container directory to use for all mounts and files.
  - mount_home: if true, mounts the user's $HOME directory into the container
    to `/home/$USERNAME`. If False, nothing.
  - run_options: extra kv pairs to supply to `docker run`.
  - shell_cmd: command of the shell to install into the container. Also used as
    the entrypoint if that's not supplied.
  - entrypoint: command to run. Defaults to the shell_cmd.
  - image_id: ID of the image to run. Supplying this will skip an image build.

  any extra kwargs supplied are passed through to build_image.

  TODO image_id should be image_build_fn, and default to build_image. Then
  image_id can be a function that returns a constant.

  """
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if mount_home is None:
    mount_home = True

  if run_options is None:
    run_options = {}

  if entrypoint_args is None:
    entrypoint_args = []

  if shell_cmd is None:
    # Only set a default shell if we're also mounting the home volume.
    # Otherwise a custom shell won't have access to the user's profile.
    shell_cmd = default_shell() if mount_home else "/bin/bash"

  if entrypoint is None:
    entrypoint = shell_cmd

  if image_id is None:
    image_id = build_image(use_gpu,
                           workdir=workdir,
                           shell_cmd=shell_cmd,
                           **kwargs)

  run_opts = _interactive_opts(workdir, {
      "-it": None,
      "--entrypoint": entrypoint
  })
  run_opts.update(run_options)

  command = _run_cmd(use_gpu) + u.expand_args(run_opts) + _home_mount_cmds(
      mount_home) + [image_id] + entrypoint_args
  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)


def run_notebook(use_gpu: bool,
                 port: Optional[int] = None,
                 lab: Optional[bool] = None,
                 version: Optional[bool] = None,
                 **kwargs) -> None:
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

  kwargs are all extra arguments taken by run_interactive.

  """

  if port is None:
    port = 8888

  if lab is None:
    lab = False

  jupyter_cmd = "lab" if lab else "notebook"
  args = [
      "-m", "jupyter", jupyter_cmd, "--ip=0.0.0.0", f"--port={port}",
      "--no-browser"
  ]

  run_interactive(use_gpu,
                  entrypoint="/opt/venv/bin/python",
                  entrypoint_args=args,
                  run_options={"-p": f"{port}:{port}"},
                  inject_notebook=True,
                  jupyter_version=version,
                  **kwargs)


def submit_local(use_gpu: bool,
                 package: u.Package,
                 args: Optional[List[str]] = None,
                 **kwargs) -> None:
  """Build and run a docker container locally that executes the supplied package
  as its entrypoint and passes through all arguments in args.

  kwargs are all extra arguments taken by build_image.

  """
  if args is None:
    args = []

  image_id = build_image(use_gpu, package=package, **kwargs)
  command = _run_cmd(use_gpu) + [image_id] + args

  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)
