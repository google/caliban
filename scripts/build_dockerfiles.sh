#!/bin/bash -eu
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/bin/bash

# Error out if any of the commands fail.
set -e

# GPU base-base, with all CUDA dependencies required for GPU work. Built off of the NVIDIA base image.
docker build -t gcr.io/blueshift-playground/blueshift:gpu-base -f- . <dockerfiles/Dockerfile.gpu
docker push gcr.io/blueshift-playground/blueshift:gpu-base

# CPU base image for jobs.
docker build -t gcr.io/blueshift-playground/blueshift:cpu -f- . <dockerfiles/Dockerfile
docker push gcr.io/blueshift-playground/blueshift:cpu

# GPU image.
docker build --build-arg BASE_IMAGE=gcr.io/blueshift-playground/blueshift:gpu-base -t gcr.io/blueshift-playground/blueshift:gpu -f- . <dockerfiles/Dockerfile
docker push gcr.io/blueshift-playground/blueshift:gpu
