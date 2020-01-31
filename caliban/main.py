"""Entry point for Caliban's various modes."""

from __future__ import absolute_import, division, print_function

import logging as ll
import os
import sys

from absl import app, logging

import caliban.cli as cli
import caliban.cloud.core as cloud
import caliban.config as c
import caliban.docker as docker
import caliban.util as u
import caliban.gke as gke
import caliban.gke.cli

ll.getLogger('caliban.main').setLevel(logging.ERROR)


def run_app(arg_input):
  """Main function to run the Caliban app. Accepts a Namespace-type output of an
  argparse argument parser.

  """
  args = vars(arg_input)
  script_args = c.extract_script_args(args)

  command = args["command"]

  if command == "cluster":
    return gke.cli.run_cli_command(args)

  job_mode = cli.resolve_job_mode(args)
  docker_args = cli.generate_docker_args(job_mode, args)
  docker_run_args = args.get("docker_run_args", [])

  if command == "shell":
    mount_home = not args['bare']
    image_id = args.get("image_id")
    shell = args['shell']
    docker.run_interactive(job_mode,
                           image_id=image_id,
                           run_args=docker_run_args,
                           mount_home=mount_home,
                           shell=shell,
                           **docker_args)

  elif command == "notebook":
    port = args.get("port")
    lab = args.get("lab")
    version = args.get("jupyter_version")
    mount_home = not args['bare']
    docker.run_notebook(job_mode,
                        port=port,
                        lab=lab,
                        version=version,
                        run_args=docker_run_args,
                        mount_home=mount_home,
                        **docker_args)

  elif command == "build":
    package = args["module"]
    docker.build_image(job_mode, package=package, **docker_args)

  elif command == "run":
    dry_run = args["dry_run"]
    package = args["module"]
    image_id = args.get("image_id")
    exp_config = args.get("experiment_config")

    docker.run_experiments(job_mode,
                           run_args=docker_run_args,
                           script_args=script_args,
                           image_id=image_id,
                           experiment_config=exp_config,
                           dry_run=dry_run,
                           package=package,
                           **docker_args)

  elif command == "cloud":
    project_id = c.extract_project_id(args)
    region = c.extract_region(args)

    dry_run = args["dry_run"]
    package = args["module"]
    job_name = args.get("name")
    gpu_spec = args.get("gpu_spec")
    tpu_spec = args.get("tpu_spec")
    image_tag = args.get("image_tag")
    machine_type = args.get("machine_type")
    exp_config = args.get("experiment_config")
    labels = u.sanitize_labels(args.get("label") or [])

    # Arguments to internally build the image required to submit to Cloud.
    docker_m = {"job_mode": job_mode, "package": package, **docker_args}

    cloud.submit_ml_job(job_mode=job_mode,
                        docker_args=docker_m,
                        region=region,
                        project_id=project_id,
                        dry_run=dry_run,
                        job_name=job_name,
                        machine_type=machine_type,
                        gpu_spec=gpu_spec,
                        tpu_spec=tpu_spec,
                        image_tag=image_tag,
                        labels=labels,
                        script_args=script_args,
                        experiment_config=exp_config)
  else:
    logging.info(f"Unknown command: {command}")
    sys.exit(1)


def main():
  logging.use_python_logging()
  try:
    app.run(run_app, flags_parser=cli.parse_flags)
  except KeyboardInterrupt:
    logging.info('Shutting down.')
    sys.exit(0)


if __name__ == '__main__':
  main()
