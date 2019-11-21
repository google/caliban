# 0.1.2

- all local Docker commands now run `--ipc host`, which gives `docker run`
  access to all of the host's memory.
- Base images now contain `gsutil`. `docker.py` automatically configures
  `gcloud` and `gsutil` with shared credentials when they're present on the
  machine running caliban commands.
