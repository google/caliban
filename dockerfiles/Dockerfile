# Copyright 2020-2023 Google LLC
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

ARG BASE_IMAGE=ubuntu:22.04

FROM $BASE_IMAGE
MAINTAINER Sam Ritchie <sam@mentat.org>

ARG GCLOUD_ARCHIVE=google-cloud-cli-441.0.0-linux-x86_64.tar.gz
ARG GCLOUD_LOC=/usr/local/gcloud
ARG JULIA_LOC=/usr/local/julia
ARG PYTHON_VERSION=3.10
ARG JULIA_VERSION=1.9.2
ARG ARCH=x86_64

# minicoda release archive is here: https://repo.anaconda.com/miniconda
# see the docs here for managing python versions with conda:
# https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-python.html
ARG MINICONDA_VERSION=py310_23.5.2-0

LABEL maintainer="sam@mentat.org"

# Install git so that users can declare git dependencies, and python3 so
# miniconda we can generate an isolated Python environment inside the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    cmake \
    ca-certificates \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Some tools expect a "python" binary.
RUN ln -s $(which python${PYTHON_VERSION}) /usr/local/bin/python

# install the google cloud SDK.
RUN wget -nv \
    https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/${GCLOUD_ARCHIVE} && \
    mkdir -m 777 ${GCLOUD_LOC} && \
    tar xvzf ${GCLOUD_ARCHIVE} -C ${GCLOUD_LOC} && \
    rm ${GCLOUD_ARCHIVE} && \
    ${GCLOUD_LOC}/google-cloud-sdk/install.sh --usage-reporting=false \
    --path-update=false --bash-completion=false \
    --disable-installation-options && \
    rm -rf /root/.config/* && \
    ln -s /root/.config /config && \
    # Remove the backup directory that gcloud creates
    rm -rf ${GCLOUD_LOC}/google-cloud-sdk/.install/.backup

# Add the Cloud SDK to the path:
ENV PATH $PATH:${GCLOUD_LOC}/google-cloud-sdk/bin

COPY scripts/bashrc /etc/bash.bashrc

# Install Miniconda and prep the system to activate our custom environment.
RUN wget -nv https://repo.anaconda.com/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-${ARCH}.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -u -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -afy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> /etc/bash.bashrc && \
    echo "conda activate caliban" >> /etc/bash.bashrc

RUN yes | /opt/conda/bin/conda create \
    --name caliban python=${PYTHON_VERSION} \
    && /opt/conda/bin/conda clean --all

## This allows a user to:
# - read the system-wide bashrc file
# - install packages into the conda environment once it launches.
RUN chmod -R 644 /etc/bash.bashrc \
    && chmod -R 757 /opt/conda/envs/caliban \
    && mkdir /.cache \
    && chmod -R 757 /.cache

# This is equivalent to activating the env.
ENV PATH /opt/conda/envs/caliban/bin:$PATH

# This makes pip recognize our conda environment
# as a virtual environment, so it installs editables properly
# See https://github.com/conda/conda/issues/5861 for details
ENV PIP_SRC /opt/conda/envs/caliban/pipsrc

# introduced in pip 22.1, silences the warning since we are NOT using root.
ENV PIP_ROOT_USER_ACTION ignore
