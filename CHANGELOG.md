# 0.1.3

This version:

- Moves from batch submission to submitting 1 request at a time, so Cloud can handle our rate limiting
- adds support for lists of experiment configs
- adds terminal highlighting
- adds a progress bar for Cloud submissions
- cleans up the terminal output for each job to show the interesting bits, not the entire training spec.
- moves the job index to the end of the jobId, so searching is easier

If you like you can set `-v 1` to see the full spec output.

# 0.1.2

- `caliban.cloud.types` has lots of enums and types that make it easier to code
  well against AI Platform.
- `caliban cloud` has more validations, now.
- `caliban cloud` now supports:
  - `--gpu_spec`, which you can use to configure the GPU count and type for your
    job.
  - `--machine_type` allows you to specify the machine type for all jobs that
    run.
  - `--experiment_config` lets you submit batches of jobs at once.
  - `--force` skips all validations and forces a submission with the specified
    config.
  - `--dry_run` will generate logs showing what WOULD happen if you submit a
    batch of jobs.
- The `caliban cloud --stream_logs` argument is now gone; the command prints,
  so this is easy enough to run without special help, and the argument made
  batch job submission difficult.
- all local Docker commands now run `--ipc host`, which gives `docker run`
  access to all of the host's memory.
- Base images now contain `gsutil`. `docker.py` automatically configures
  `gcloud` and `gsutil` with shared credentials when they're present on the
  machine running caliban commands.
