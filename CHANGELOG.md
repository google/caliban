# pending

# 0.4.1

Small release to archive for JOSS acceptance.

- Move `cloud_sql_proxy` installation before code copy (https://github.com/google/caliban/pull/87)

# 0.4.0

The biggest feature in this new release is native support for logging to an
MLFlow tracking server using the [UV
Metrics](http://github.com/google/uv-metrics) project.
(https://github.com/google/caliban/pull/35) This feature is in alpha; expect
documentation soon.

### More features

- minor bugfixes for GKE (https://github.com/google/caliban/pull/85)
- additional tests for gke.{types, util} (https://github.com/google/caliban/pull/84)
- re-order custom apt packages before pip requirements (https://github.com/google/caliban/pull/82)
- modify base image to our more general cloudbuild naming scheme (https://github.com/google/caliban/pull/80)
- updated `google-auth` dependency version to `1.19.0` (https://github.com/google/caliban/pull/79)
- add clearer contribution info (https://github.com/google/caliban/pull/76)
- Update uv-metrics tutorial (https://github.com/google/caliban/pull/74, https://github.com/google/caliban/pull/72)
- add support for running an embedded cloudsql_proxy (https://github.com/google/caliban/pull/60)
- bugfix for #65: do not add resource maxima when quota is < 1 (#67)
- Updated accelerator regions (and globally availabe AI Platform regions to
  match the current state here):
  https://cloud.google.com/ai-platform/training/docs/regions

# 0.3.0

- @ramasesh Added a fix that prevented `pip` git dependencies from working in
  `caliban shell` mode (https://github.com/google/caliban/pull/55) This adds a
  small update to the base image, so be sure to run

```
docker pull gcr.io/blueshift-playground/blueshift:cpu
docker pull gcr.io/blueshift-playground/blueshift:gpu
```

to get access to this fix.

- Thanks to @eschnett, `--docker_run-args` can now deal with arbitrary
  whitespace in the list of arguments, instead of single spaces only.
  (https://github.com/google/caliban/pull/46)

- Caliban now authenticates AI Platform job submissions using the authentication
  provided by `gcloud auth login`, rather than requiring a service account key.
  This significantly simplifies the setup required for a first time user.

- `caliban cloud` now checks if the image exists remotely before issuing a
  `docker push` command on the newly built image
  (https://github.com/google/caliban/pull/36)

- Big internal refactor to make it easier to work on code, increase test
  coverage, add new backends (https://github.com/google/caliban/pull/32)

- add `schema` validation for `.calibanconfig.json`. This makes it much easier
  to add configuration knobs: https://github.com/google/caliban/pull/37

- Custom base image support (https://github.com/google/caliban/pull/39), thanks
  to https://github.com/google/caliban/pull/20 from @sagravat.
  `.calibanconfig.json` now supports a `"base_image"` key. For the value, can
  supply:
  - a Docker base image of your own
  - a dict of the form `{"cpu": "base_image", "gpu": "base_image"}` with both
    entries optional, of course.

  Two more cool features.

  First, if you use a format string, like `"my_image-{}:latest"`, the format
  block `{}` will be filled in with either `cpu` or `gpu`, depending on the mode
  Caliban is using.

  Second, we now have native support for [Google's Deep Learning
  VMs](https://cloud.google.com/ai-platform/deep-learning-vm/docs/introduction)
  as base images. The actual VM containers [live
  here](https://console.cloud.google.com/gcr/images/deeplearning-platform-release/GLOBAL).
  If you provide any of the following strings, Caliban will expand them out to
  the actual base image location:

```
dlvm:pytorch-cpu
dlvm:pytorch-cpu-1.0
dlvm:pytorch-cpu-1.1
dlvm:pytorch-cpu-1.2
dlvm:pytorch-cpu-1.3
dlvm:pytorch-cpu-1.4
dlvm:pytorch-gpu
dlvm:pytorch-gpu-1.0
dlvm:pytorch-gpu-1.1
dlvm:pytorch-gpu-1.2
dlvm:pytorch-gpu-1.3
dlvm:pytorch-gpu-1.4
dlvm:tf-cpu
dlvm:tf-cpu-1.0
dlvm:tf-cpu-1.13
dlvm:tf-cpu-1.14
dlvm:tf-cpu-1.15
dlvm:tf-gpu
dlvm:tf-gpu-1.0
dlvm:tf-gpu-1.13
dlvm:tf-gpu-1.14
dlvm:tf-gpu-1.15
dlvm:tf2-cpu
dlvm:tf2-cpu-2.0
dlvm:tf2-cpu-2.1
dlvm:tf2-cpu-2.2
dlvm:tf2-gpu
dlvm:tf2-gpu-2.0
dlvm:tf2-gpu-2.1
dlvm:tf2-gpu-2.2
```

Format strings work here as well! So, `"dlvm:pytorch-{}-1.4"` is a totally valid
base image.

# 0.2.6

- Prepared for a variety of base images by setting up a cloud build matrix:
  https://github.com/google/caliban/pull/25
- Added better documentation for `gcloud auth configure-docker`
  https://github.com/google/caliban/pull/26
- Added `close()` to `TqdmFile`, preventing an error when piping `stdout`:
  https://github.com/google/caliban/pull/30
- `tqdm` progress bars and other interactive outputs now display correctly in
  `caliban run` outputs. `stdout` flushes properly! Before these changes,
  `stderr` would appear before any `stdout`, making it difficult to store the
  logs in a text file. Now, by default, python processes launched by `caliban
  run` won't buffer. https://github.com/google/caliban/pull/31

![2020-06-26 09 48 50](https://user-images.githubusercontent.com/69635/85877300-2a3e7300-b794-11ea-9792-4cf3ae5e4263.gif)

# 0.2.5

- fixes the python binary that caliban notebook points to (now that we use
  conda)
- adds DEBIAN_FRONTEND=noninteractive to the apt-get command, so that packages
  like texlive won't freeze and wait for you to specify a timezone.

This makes it easy to add, for example, npm and latex support to your caliban
notebook invocations.

# 0.2.4

- fixes a bug with `parse_region` not handling a lack of default.
- converts the build to Github Actions.
- Rolls Caliban back to requiring only python 3.6 support.
- Removes some unused imports from a few files.

# 0.2.3

- Added fix for an issue where large user IDs would crash Docker during the
  build phase. https://github.com/google/caliban/pull/8

# 0.2.2

- Fix for bug with requirements.txt files.

# 0.2.1

- Added support for Conda dependencies
  (https://github.com/google/caliban/pull/5). If you include `environment.yml`
  in your project's folder Caliban will attempt to install all dependencies.
- Caliban now uses a slimmer base image for GPU mode.
- Base images for CPU and GPU modes now use Conda to manage the container's
  virtual environment instead of `virtualenv`.

# 0.2.0

- Caliban now caches the service account key and ADC file; you should see faster
  builds, BUT you might run into trouble if you try to run multiple Caliban
  commands in the same directory in different processes, due to a race condition
  with a temp file dropped in the directory. If you see a failure, try again.
- Private Cloud Source Repositories are now supported as requirements in the
  `requirements.txt` and `setup.py` of projects executed using Caliban.
- `caliban notebook` now installs `jupyter` instead of `jupyterlab`. `caliban
  notebook --lab` of course still uses `jupyterlab`.
- Caliban now works with Python 3.5.
- The default release channel for gke clusters in caliban is now 'regular', as
  node autoprovisioning now works with preemptible instances in the regular
  channel.
- If you provide `--cloud_key` Caliban will now properly use the supplied cloud
  key to submit jobs to AI platform. Previously, Caliban would rely on the
  system's auth method, which made it impossible to point to a different
  project if your current service account key wasn't the owner.
- Changed gke job submission to accept min cpu and min mem arguments instead
  of an explicit machine-type. This allows gke to efficiently schedule jobs
  and prevents issues where jobs can be oversubscribed on compute nodes.
- added support for `.calibanconfig.json`. You can now add this file with an
  `"apt_packages"` entry to specify aptitude packages to install inside the
  container. The value under this key can be either a list, or a dictionary with
  `"gpu"` and `"cpu"'` keys. For example, any of the following are valid:

```
# This is a list by itself. Comments are fine, by the way.
{
     "apt_packages": ["libsm6", "libxext6", "libxrender-dev"]
}
```

This works too:

```
# You can also include a dictionary with different deps
# for gpu and cpu modes. It's fine to leave either of these blank,
# or not include it.
{
    "apt_packages": {
        "gpu": ["libsm6", "libxext6", "libxrender-dev"],
        "cpu": ["some_other_package"]
    }
}
```

# 0.1.15

- `caliban notebook` now attempts to search for the first free port instead of
  failing due to an already-occupied port.

- `pip` is now called with `--no-cache-dir` inside the container; this should
  shrink container sizes with no impact on performance.

- All commands have a new `--no-cache` option; when supplied, Docker will skip
  using its build cache. This is helpful to use if you want to, say, force new
  dependencies to get installed without bumping their versions explicitly.

# 0.1.14

- JSON experiment configuration files can now handle arguments which are varied
  together, by supplying a compound key, of the form e.g. `[arg1,arg2]`.

- better error messages print when a docker command fails.

- Caliban can now handle pushing containers to "domain scoped projects":
  https://cloud.google.com/container-registry/docs/overview#domain-scoped_projects
  The colon in the project name separating domain and project ID is handled
  properly.

# 0.1.13

- 'caliban run' and 'caliban shell' now take an --image_id argument; if
  provided, these commands will skip their 'docker build' phase and use the
  image ID directly.

- AI Platform labels now swap periods for underscores (thanks to vinay@!); this
  means that floating point numbers will no longer have pre- and post- decimal
  components concatenated.

- A new `expansion` script will expand experiment configs into all of the
  individual experiments they'd generate. This command can accept `stdin`, just
  like the `--experiment_config` argument. Options include `--pprint` and
  `--print_flags`. The output of this script can be piped directly into `caliban
  cloud --experiment_config stdin`.

- `caliban shell` will now default to bash if you're using a shell that's not
  `bash` or `zsh` (fish shell, for example) instead of erroring out.

- `caliban shell` has a new `--shell` argument that you can use to override the
  container's default shell.

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
- moved some methods from cluster/cluster.py to gke/utils.py
- added unit tests for some gke/utils.py methods
- Support for ADC credentials! if application_default_credentials.json is
  present on the user's machine, they now get copied into the container.
- if ADC credentials are NOT present but a service account key is we write a
  placeholder. this is required to get ctpu working inside containers.

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
