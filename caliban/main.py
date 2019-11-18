"""Docker and AI Platform model training and development script.

Run like this in the hello-world project for an example:

# Start a shell:
caliban shell

# Watch a local job fail, since it no longer has local access.
caliban run trainer.train

# Run a local job on the Mac via Docker successfully:
caliban run -e cpu --nogpu trainer.train -- --epochs 2 --data_path gs://$BUCKET_NAME/data/mnist.npz

# Submit a remote job
caliban cloud -e gpu trainer.train -- --epochs 2 --data_path gs://$BUCKET_NAME/data/mnist.npz
"""

from __future__ import absolute_import, division, print_function

import logging as ll
import os
import sys

from absl import app, logging

import caliban.cli as cli
import caliban.cloud as cloud
import caliban.config as c
import caliban.docker as docker
import caliban.util as u

ll.getLogger('caliban.main').setLevel(logging.ERROR)


def mac_gpu_check(mode: str, use_gpu: bool):
  """If the command depends on 'docker run' and is running on a Mac, fail
fast."""
  if use_gpu and mode in ("shell", "notebook", "run"):
    print(f"'caliban {mode}' doesn't support GPU usage on Macs! Please pass \
--nogpu to use this command.")
    print()
    print(
        "GPU mode is fine for 'caliban cloud' from a mac; just nothing that runs \
locally.")
    sys.exit(1)


def run_app(arg_input):
  """Any argument not absorbed by Abseil's flags gets passed along to here.
  """
  args = vars(arg_input)
  script_args = c.extract_script_args(args)

  command = args["command"]
  use_gpu = args["gpu"]

  if u.is_mac():
    mac_gpu_check(command, use_gpu)

  # Get extra dependencies in case you want to install your requirements via a
  # setup.py file.
  setup_extras = None
  if os.path.exists("setup.py"):
    setup_extras = args.get("extras") or []

  creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

  reqs = "requirements.txt"
  template_args = {
      "requirements_path": reqs if os.path.exists(reqs) else None,
      "credentials_path": creds_path,
      "setup_extras": setup_extras,
      "extra_dirs": args.get("dirs")
  }

  if command == "shell":
    mount_home = not args['bare']
    docker.run_interactive(use_gpu, mount_home=mount_home, **template_args)

  elif command == "notebook":
    port = args.get("port")
    lab = args.get("lab")
    mount_home = not args['bare']
    docker.run_notebook(use_gpu,
                        port=port,
                        lab=lab,
                        mount_home=mount_home,
                        **template_args)

  elif command == "run":
    package = args["module"]
    docker.submit_local(use_gpu, package, script_args, **template_args)

  elif command == "cloud":
    # TODO These have defaults... the project default is probably not good. We
    # should error if this doesn't exist.
    project_id = os.environ.get("PROJECT_ID", "research-3141")
    region = os.environ.get("REGION", "us-central1")

    stream_logs = args["stream_logs"]
    package = args["module"]
    job_name = args.get("name")
    labels = u.sanitize_labels(args.get("label") or [])

    cloud.submit_package(use_gpu,
                         package,
                         region,
                         project_id,
                         stream_logs=stream_logs,
                         script_args=script_args,
                         job_name=job_name,
                         labels=labels,
                         **template_args)
  else:
    logging.info(f"Unknown command: {command}")
    sys.exit(1)


def main():
  app.run(run_app, flags_parser=cli.parse_flags)


if __name__ == '__main__':
  main()
