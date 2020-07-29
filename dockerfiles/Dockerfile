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

# This builds the base images that we can use for development at Blueshift.
# Tensorflow 2.1 by default, but we can override the image when we call docker.
#
# docker build -t gcr.io/blueshift-playground/blueshift:cpu -f- . <Dockerfile
#
# docker push gcr.io/blueshift-playground/blueshift:cpu
#
# docker build --build-arg BASE_IMAGE=tensorflow/tensorflow:2.1.0-gpu-py3 -t gcr.io/blueshift-playground/blueshift:gpu -f- . <Dockerfile
#
# docker push gcr.io/blueshift-playground/blueshift:gpu
#
#  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/tools/dockerfiles/assembler.py

ARG BASE_IMAGE=ubuntu:18.04

FROM $BASE_IMAGE
MAINTAINER Sam Ritchie <sritchie09@gmail.com>

ARG GCLOUD_LOC=/usr/local/gcloud
ARG PYTHON_VERSION=3.7

# minicoda release archive is here: https://repo.anaconda.com/miniconda
# see the docs here for managing python versions with conda:
# https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-python.html
ARG MINICONDA_VERSION=py37_4.8.2

LABEL maintainer="samritchie@google.com"

# See http://bugs.python.org/issue19846
ENV LANG C.UTF-8

# Install git so that users can declare git dependencies, and python3 plus
# python3-virtualenv so we can generate an isolated Python environment inside
# the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  python3 \
  python3-virtualenv \
  wget && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Some tools expect a "python" binary.
RUN ln -s $(which python3) /usr/local/bin/python

# install the google cloud SDK.
RUN wget -nv \
  https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz && \
  mkdir -m 777 ${GCLOUD_LOC} && \
  tar xvzf google-cloud-sdk.tar.gz -C ${GCLOUD_LOC} && \
  rm google-cloud-sdk.tar.gz && \
  ${GCLOUD_LOC}/google-cloud-sdk/install.sh --usage-reporting=false \
  --path-update=false --bash-completion=false \
  --disable-installation-options && \
  rm -rf /root/.config/* && \
  ln -s /root/.config /config && \
  # Remove the backup directory that gcloud creates
  rm -rf ${GCLOUD_LOC}/google-cloud-sdk/.install/.backup

# Path configuration
ENV PATH $PATH:${GCLOUD_LOC}/google-cloud-sdk/bin

COPY scripts/bashrc /etc/bash.bashrc

# Install Miniconda and prep the system to activate our custom environment.
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh -O ~/miniconda.sh && \
  /bin/bash ~/miniconda.sh -b -p /opt/conda && \
  rm ~/miniconda.sh && \
  /opt/conda/bin/conda clean -tipsy && \
  ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
  echo ". /opt/conda/etc/profile.d/conda.sh" >> /etc/bash.bashrc && \
  echo "conda activate caliban" >> /etc/bash.bashrc

RUN yes | /opt/conda/bin/conda create --name caliban python=${PYTHON_VERSION} && /opt/conda/bin/conda clean --all

# This allows a user to install packages in the conda environment once it
# launches.
RUN chmod -R 757 /opt/conda/envs/caliban && mkdir /.cache && chmod -R 757 /.cache

# This is equivalent to activating the env.
ENV PATH /opt/conda/envs/caliban/bin:$PATH

# This makes pip recognize our conda environment
# as a virtual environment, so it installs editables properly
# See https://github.com/conda/conda/issues/5861 for details
ENV PIP_SRC /opt/conda/envs/caliban/pipsrc
