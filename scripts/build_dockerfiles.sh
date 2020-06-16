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

docker build -t gcr.io/blueshift-playground/blueshift:cpu -f- . <Dockerfile
docker push gcr.io/blueshift-playground/blueshift:cpu
docker build --build-arg BASE_IMAGE=tensorflow/tensorflow:2.2.0-gpu -t gcr.io/blueshift-playground/blueshift:gpu -f- . <Dockerfile
docker push gcr.io/blueshift-playground/blueshift:gpu
