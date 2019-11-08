"""Cloud utilities."""

from __future__ import absolute_import, division, print_function

import datetime
from typing import List, Optional
import subprocess

import caliban.docker as d
from absl import app, logging
from googleapiclient import discovery, errors


def create_ml_job(job_spec, parent):
  """This submits the actual job."""
  ml = discovery.build('ml', 'v1')
  request = ml.projects().jobs().create(body=job_spec, parent=parent)

  try:
    response = request.execute()
    logging.info("Request succeeded!")
    logging.info(response)
    return response

  except errors.HttpError as err:
    logging.error("There was an error submitting the job. Check the details:")
    logging.error(err._get_reason())


def _stream_cmd(job_id: str) -> List[str]:
  return ["gcloud", "ai-platform", "jobs", "stream-logs", job_id]


def stream_ml_logs(job_id: str) -> None:
  """
  TODO this should validate whether or not the job actually exists.
  """
  subprocess.call(_stream_cmd(job_id))


def submit_package(use_gpu: bool,
                   package: d.Package,
                   region: str,
                   project_id: str,
                   stream_logs: bool = True,
                   script_args: Optional[List[str]] = None,
                   creds_path: Optional[str] = None) -> None:
  """Submit a container to the cloud.

  Cloud API docs for the endpoint we use here:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs/create

  Use this when we configure hyper-parameter sweeps to run lots of experiments:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#hyperparameterspec
  """
  if script_args is None:
    script_args = []

  # TODO make this configurable. BUT bake in knowledge from the links below
  # about what regions actually support GPU usage.
  master_type = "standard_p100" if use_gpu else "complex_model_l"

  # TODO take a custom job name.
  timestamp = datetime.datetime.now().strftime('_%Y_%m_%d_%H_%M_%S')
  job_id = f"test_job_{timestamp}"

  logging.info(
      f"Running remote job with {use_gpu} and {package}, args: {script_args}")

  image_id = d.build_image(use_gpu, package, credentials_path=creds_path)
  image_tag = d.push_uuid_tag(project_id, image_id)

  training_input = {
      # https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#ReplicaConfig
      #
      # Also the GPU compatibility table. This is important for when we upgrade
      # from the legacy machine definition.
      # https://cloud.google.com/ml-engine/docs/using-gpus#gpu-compatibility-table
      #
      # This is also where we can do some work if we do want to support TPUs.
      "masterConfig": {
          "imageUri": image_tag
      },
      "scaleTier": "CUSTOM",
      "masterType": master_type,
      "args": script_args,
      "region": region
  }
  job_spec = {"jobId": job_id, "trainingInput": training_input}

  # Store the full project ID in a variable in the format the API needs.
  parent = f"projects/{project_id}"

  create_ml_job(job_spec, parent)

  logging.info(f"Job submission successful for job ID {job_id}")
  stream_command = " ".join(_stream_cmd(job_id))

  if stream_logs:
    logging.info(f"""Streaming logs for {job_id}.

Feel free to kill this process. You can always resume streaming by running:

{stream_command}

(Also note that the log streamer will NOT exit when the job completes!)
    """)
    stream_ml_logs(job_id)
  else:
    logging.info("""You can stream the logs with the following command:

{stream_command}
""")
    logging.info(stream_command)
