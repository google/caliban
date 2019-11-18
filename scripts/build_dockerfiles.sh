#!/bin/bash

# Error out if any of the commands fail.
set -e

docker build -t gcr.io/blueshift-playground/blueshift:cpu -f- . <Dockerfile
docker push gcr.io/blueshift-playground/blueshift:cpu
docker build --build-arg BASE_IMAGE=tensorflow/tensorflow:2.0.0-gpu-py3 -t gcr.io/blueshift-playground/blueshift:gpu -f- . <Dockerfile
docker push gcr.io/blueshift-playground/blueshift:gpu
