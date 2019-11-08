"""Docker utilities.

NOTE - if I do use the Docker python API, then adding --runtime=nvidia is enough
to get the GPU stuff going.


docker run --runtime=nvidia --rm nvidia/cuda:9.0-runtime nvidia-smi

"""

from __future__ import absolute_import, division, print_function

import collections
import os
import subprocess
from typing import Dict, List, Optional

from absl import logging

import caliban.util as u

Package = collections.namedtuple('Package', ['package_path', 'main_module'])

DEV_CONTAINER_ROOT = "gcr.io/blueshift-playground/blueshift"
TF_VERSIONS = {"2.0.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR = "/usr/app"
CREDS_DIR = "/.creds"


def base_image_suffix(use_gpu: bool) -> str:
  return "gpu" if use_gpu else "cpu"


def base_image_id(use_gpu: bool) -> str:
  return "{}:{}".format(DEV_CONTAINER_ROOT, base_image_suffix(use_gpu))


def _package_entries(workdir: str, user_id: int, user_group: int,
                     package: Package) -> str:
  owner = f"{user_id}:{user_group}"
  return f"""
# Copy all project code into the docker container.
# TODO note that we need this to be a relative directory!
COPY --chown={owner} {package.package_path} {workdir}/{package.package_path}

# Declare an entrypoint that actually runs the container.
ENTRYPOINT ["python", "-m", "{package.main_module}"]
  """


def _credentials_entries(credentials_path: str, user_id: int,
                         user_group: int) -> str:
  docker_creds = f"{CREDS_DIR}/credentials.json"
  return f"""
COPY --chown={user_id}:{user_group} {credentials_path} {docker_creds}

ENV GOOGLE_APPLICATION_CREDENTIALS={docker_creds}
"""


def _dockerfile_template(workdir: str,
                         use_gpu: bool,
                         package: Optional[Package] = None,
                         credentials_path: Optional[str] = None) -> str:
  """This generates a Dockerfile that installs the dependencies that this package
  needs to create a local base image for development. The goal here is to make
  it fast to reboot within a particular project.


  TODO move this out to a template that we pull in.
  """
  uid = os.getuid()
  gid = os.getgid()
  image_id = base_image_id(use_gpu)

  dockerfile = f"""
FROM {image_id}

# The directory is created by root. This sets permissions so that any user can
# access the folder.
RUN mkdir -m 777 {workdir} {CREDS_DIR}

# You CAN remove the chown stuff if you're sure you're never going to pip
# install inside the container as the user. That would allow us to cache this
# step across various users. Maybe that's not necessary.
COPY --chown={uid}:{gid} setup.py {workdir}

WORKDIR {workdir}

USER {uid}:{gid}

# TODO handle installation for requirements.txt, or various submodules. This
# current example has a hardcoded tf2 extra.
RUN /bin/bash -c "pip install .[tf2]"
"""
  if credentials_path is not None:
    dockerfile += _credentials_entries(credentials_path, uid, gid)

  if package is not None:
    dockerfile += _package_entries(workdir, uid, gid, package)
  return dockerfile


def tf_base_image(tensorflow_version, use_gpu):
  """Returns the base image to use, depending on whether or not we're utilizing a
  GPU. This is JUST for building our base images for Blueshift; not for actually
  using in a job.

  List of available tags: https://hub.docker.com/r/tensorflow/tensorflow/tags
  """
  if tensorflow_version in TF_VERSIONS:
    gpu = "-gpu" if use_gpu else ""
    return "tensorflow/tensorflow:{}{}-py3".format(tensorflow_version, gpu)
  else:
    raise Exception(
        "{} is not a valid tensorflow version. Try one of: {}".format(
            tensorflow_version, TF_VERSIONS))


def docker_image_id(output: str) -> str:
  """Parses the Docker image ID from an untagged build, completed successfully.
  """
  return output.splitlines()[-1].split()[-1]


def build_image(use_gpu: bool,
                package: Optional[Package] = None,
                workdir: Optional[str] = None,
                credentials_path: Optional[str] = None) -> str:
  """Better way of building a docker image.
"""
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  with u.TempCopy(credentials_path) as cred_path:
    cmd = ["docker", "build", "--rm", "-f-", os.getcwd()]
    dockerfile = _dockerfile_template(workdir,
                                      use_gpu,
                                      package=package,
                                      credentials_path=cred_path)

    logging.info(f"Running command: {' '.join(cmd)}")

    try:
      output = u.capture_stdout(cmd, input_str=dockerfile)
      return docker_image_id(output)

    except subprocess.CalledProcessError as e:
      logging.error(e.output)
      logging.error(e.stderr)


def push_uuid_tag(project_id: str, image_id: str) -> str:
  """Takes a base image and tags it for upload, then pushes it to our remote
  repository.
  """
  image_tag = f"gcr.io/{project_id}/{image_id}:latest"
  subprocess.run(["docker", "tag", image_id, image_tag], check=True)
  subprocess.run(["docker", "push", image_tag], check=True)
  return image_tag


def _run_cmd(use_gpu: bool) -> List[str]:
  runtime = ["--runtime", "nvidia"] if use_gpu else []
  return ["docker", "run"] + runtime


def local_base_args(workdir: str,
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


def submit_local(use_gpu: bool,
                 package: Package,
                 args: Optional[List[str]] = None,
                 workdir: Optional[str] = None,
                 creds_path: Optional[str] = None) -> None:
  """For now... first build, then submit. But we really want to do something
  else.
  """
  if args is None:
    args = []

  if workdir is None:
    workdir = DEFAULT_WORKDIR

  image_id = build_image(use_gpu,
                         package=package,
                         workdir=workdir,
                         credentials_path=creds_path)
  command = _run_cmd(use_gpu) + [image_id] + args

  subprocess.call(command)


def start_shell(use_gpu: bool,
                workdir: Optional[str] = None,
                image_id: Optional[str] = None,
                creds_path: Optional[str] = None) -> None:
  """Start a live interpreter.

  TODO really it should take one or the other here.
  """
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if image_id is None:
    image_id = build_image(use_gpu,
                           workdir=workdir,
                           credentials_path=creds_path)

  args = local_base_args(workdir, {"-it": None})
  command = _run_cmd(use_gpu) + u.expand_args(args) + [image_id]

  subprocess.call(command)
