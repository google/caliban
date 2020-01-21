# 0.1.12

- consolidated gke tpu/gpu spec parsing with cloud types
- modified all commands to accept as the module argument paths to arbitrary
  shell scripts. Any argument of the format "trainer.train" will execute using
  "python -m trainer.train", just as before. If instead you pass a python script
  as a file, like "trainer/train.py", caliban will execute this file inside the
  container using "python trainer/train.py". Any other argument, if it exists in
  the local directory, will be executed as a bash script.

  This allows users to run commands like "caliban cloud my_script.sh" and have
  it all work.
- "caliban run" now supports --experiment_config and --dry_run. These work just
  like they do for "caliban cloud"; the experiment config will expand out and
  execute N jobs on your local machine.

# 0.1.11

- added tpu driver specification for gke jobs
- added query for getting available tpu drivers for cluster/project

# 0.1.10

- set host_ipc=True for cluster jobs

# 0.1.9

- moved cluster constants to separate file
- moved cluster gpu validation to separate file
- added test for gpu limits validation

# 0.1.8

- TPU and GPU spec now accept validate_count arg to disable count validation.

# 0.1.7

- Fixed a bug where the label for the job name wasn't getting properly
  sanitized - this meant that if you provided an upper-cased job name job
  submission would fail.
- Fixed a bug that prevented parsing experiment config values that were floats.
- experiment config parsing now performs the full expansion at CLI-parse-time
  and validates every expanded config.

# 0.1.6

- `--docker_run_args` allows you to pass a string of arguments directly through
  to `docker run`. This command works for `caliban run`, `caliban notebook` and
  `caliban shell`.

- `docker.py` reorganized, now takes explicit `JobMode` instances throughout.

- new `--cloud_key` argument for all commands. If specified this lets you
  override the `GOOGLE_APPLICATION_CREDENTIALS` value that's usually inspected
  for the service account key.

- fixed a bug in `caliban.util.TempCopy` where a `None`-valued path would fail. This affected environments where `GOOGLE_APPLICATION_CREDENTIALS` wasn't set.

# 0.1.5

- `--experiment_config` can now take experiment configs via stdin (pipes, yay!);
  specify `--experiment_config stdin`, or any-cased version of that, and the
  script will wait to accept your input.

  As an example, this command pipes in a config and also passes `--dry_run` to
  show the series of jobs that WILL be submitted when the `--dry_run` flag is
  removed:

  ```
  cat experiment.json | caliban cloud -e gpu --experiment_config stdin --dry_run trainer.train
  ```

  You could pipe the output of a nontrivial python script that generates a JSON
  list of dicts.

- `--image_tag` argument to `caliban cloud`; if you supply this it will bypass
  the Docker build and push steps and use this image directly. This is useful if
  you want to submit a job quickly without going through a no-op build and push,
  OR if you want to broadcast an experiment to some existing container.

- if you supply a `--tpu_spec` and DON'T supply an explicit `--gpu_spec`,
  caliban will default to CPU mode. `--gpu_spec` and `--nogpu` are still
  incompatible. You can use a GPU and TPU spec together without problems.

- added support for `--tpu_spec` in `caliban cloud` mode. This validates in a
  similar style to `--gpu_spec`; any invalid combination of count, region and
  TPU type will fail.

  (Unlike `--gpu_spec` this mode IS compatible with `--nogpu`. In fact, many
  demos seem to use the non-GPU version of tensorflow here.)

- added a `caliban build` mode that simply builds the image and returns the
  image ID. Useful for checking if your image can build at all with the current
  settings.

# 0.1.4

- the CLI will now error if you pass any caliban keyword arguments AFTER the
  python module name, but before `--`. In previous versions, if you did something like

```bash
caliban cloud trainer.train --nogpu
```

  That final `--nogpu` would get passed on directly to your script, vs getting
  absorbed by Caliban.

- If you pass `--nogpu` mode and have a setup.py file, caliban will
  automatically pass `--extras cpu` and attempt to install an extras dependency
  called `cpu`. Same goes for `gpu` if you DON'T pass `--nogpu`. So, if you have
  a setup.py file, the default pip installation will now look like one of these:

```bash
pip install .[gpu]
pip install .[cpu]
```

Instead of

```
pip install .
```

# 0.1.3.1

- Minor bugfix; I was calling "len" on an iterator, not a list.

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
