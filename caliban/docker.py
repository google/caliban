"""Docker utilities.

NOTE - if I do use the Docker python API, then adding --runtime=nvidia is enough
to get the GPU stuff going.


docker run --runtime=nvidia --rm nvidia/cuda:9.0-runtime nvidia-smi

"""

from __future__ import absolute_import, division, print_function

import os
import subprocess
from typing import Dict, List, Optional

from absl import logging

import caliban.util as u

DEV_CONTAINER_ROOT = "gcr.io/blueshift-playground/blueshift"
TF_VERSIONS = {"2.0.0", "1.12.3", "1.14.0", "1.15.0"}
DEFAULT_WORKDIR = "/usr/app"
CREDS_DIR = "/.creds"


def base_image_suffix(use_gpu: bool) -> str:
  return "gpu" if use_gpu else "cpu"


def base_image_id(use_gpu: bool) -> str:
  return "{}:{}".format(DEV_CONTAINER_ROOT, base_image_suffix(use_gpu))


def extras_string(extras: List[str]) -> str:
  ret = "."
  if len(extras) > 0:
    ret += f"[{','.join(extras)}]"
  return ret


def _dependency_entries(workdir: str,
                        user_id: int,
                        user_group: int,
                        requirements_path: Optional[str] = None,
                        setup_extras: Optional[List[str]] = None) -> str:
  """setup_extras is a list of extra modules in your setup.py.... an empty list
means just install setup.py itself.
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


def _inject_notebook_template():
  return f"""
RUN pip install jupyterlab
"""


def _entry(workdir: str, user_id: int, user_group: int, dirname: str) -> str:
  owner = f"{user_id}:{user_group}"
  return f"""# Copy {dirname} into the Docker container.
COPY --chown={owner} {dirname} {workdir}/{dirname}
"""


def _extra_dir_entries(workdir: str, user_id: int, user_group: int,
                       extra_dirs: List[str]) -> str:
  ret = ""
  for d in extra_dirs:
    ret += f"\n{_entry(workdir, user_id, user_group, d)}"
  return ret


def _dockerfile_template(workdir: str,
                         use_gpu: bool,
                         package: Optional[u.Package] = None,
                         requirements_path: Optional[str] = None,
                         setup_extras: Optional[List[str]] = None,
                         credentials_path: Optional[str] = None,
                         inject_notebook: bool = False,
                         extra_dirs: Optional[List[str]] = None) -> str:
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
RUN mkdir -m 777 {workdir} {CREDS_DIR} /home/{uid}

ENV HOME=/home/{uid}

WORKDIR {workdir}

USER {uid}:{gid}
"""
  dockerfile += _dependency_entries(workdir,
                                    uid,
                                    gid,
                                    requirements_path=requirements_path,
                                    setup_extras=setup_extras)

  if inject_notebook:
    dockerfile += _inject_notebook_template()

  if credentials_path is not None:
    dockerfile += _credentials_entries(credentials_path, uid, gid)

  if extra_dirs is not None:
    dockerfile += _extra_dir_entries(workdir, uid, gid, extra_dirs)

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
                workdir: Optional[str] = None,
                credentials_path: Optional[str] = None,
                **kwargs) -> str:
  """Better way of building a docker image.
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
                 package: u.Package,
                 args: Optional[List[str]] = None,
                 **kwargs) -> None:
  """Build and run a docker container locally.

  kwargs are all extra arguments taken by dockerfile_template.
  """
  if args is None:
    args = []

  image_id = build_image(use_gpu, package=package, **kwargs)
  command = _run_cmd(use_gpu) + [image_id] + args
  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)


def start_shell(use_gpu: bool,
                workdir: Optional[str] = None,
                image_id: Optional[str] = None,
                **kwargs) -> None:
  """Start a live interpreter.

  kwargs are all extra arguments taken by dockerfile_template.
  """
  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if image_id is None:
    image_id = build_image(use_gpu, workdir=workdir, **kwargs)

  args = local_base_args(workdir, {"-it": None})
  command = _run_cmd(use_gpu) + u.expand_args(args) + [image_id]
  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)


def start_notebook(use_gpu: bool,
                   port: Optional[int] = None,
                   lab: Optional[bool] = None,
                   workdir: Optional[str] = None,
                   image_id: Optional[str] = None,
                   **kwargs) -> None:
  """Start a notebook.

  kwargs are all extra arguments taken by dockerfile_template.
  """
  if port is None:
    port = 8888

  if lab is None:
    lab = False

  if workdir is None:
    workdir = DEFAULT_WORKDIR

  if image_id is None:
    image_id = build_image(use_gpu,
                           workdir=workdir,
                           inject_notebook=True,
                           **kwargs)

  args = local_base_args(workdir, {
      "-it": None,
      "-p": f"{port}:{port}",
      "--entrypoint": "/opt/venv/bin/python"
  })
  jupyter_cmd = "lab" if lab else "notebook"
  command = _run_cmd(use_gpu) + u.expand_args(args) + [image_id] + [
      "-m", "jupyter", jupyter_cmd, "--ip=0.0.0.0", f"--port={port}",
      "--no-browser"
  ]
  logging.info(f"Running command: {' '.join(command)}")
  subprocess.call(command)
