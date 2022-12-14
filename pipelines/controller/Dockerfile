# Copyright 2022 Google LLC
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

# This creates a docker image for running the controller web-app. It is expected
# that in real use-cases, the config dir will be mounted to the host machine.

FROM eclipse-temurin:11-jdk-focal

ARG WORK_DIR="/app"
COPY target/controller-0.1.0-SNAPSHOT-exec.jar ${WORK_DIR}/controller.jar
COPY config ${WORK_DIR}/config
WORKDIR ${WORK_DIR}

# Flink will read the flink-conf.yaml file from this directory.
ENV FLINK_CONF_DIR=${WORK_DIR}/config

ENTRYPOINT java -jar /app/controller.jar
