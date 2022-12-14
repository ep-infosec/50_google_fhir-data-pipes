# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Manages uploading of FHIR resources."""

import traceback

from typing import Dict
import bundle
import fhir_client
import json
import logger_util
import pathlib
import random

class Uploader:
  """Uploads FHIR resources to either OpenMRS or any other FHIR Server."""

  def __init__(self, client: fhir_client.FhirClient):
    self.fhir_client = client
    self.logger = logger_util.create_logger(self.__class__.__module__,
                                            self.__class__.__name__)

  def fetch_location(self) -> Dict[str, str]:
    """Get map of all location_id/location_name stored in sink.

    Returns:
      Dictionary of location_id/location_name
    """
    location_map = {}
    try:
      entries = self.fhir_client.get_resource('Location')['entry']
      for entry in entries:
        location_id = entry['resource']['id']
        location_name = entry['resource']['name']
        location_map[location_id] = location_name 
      return location_map
    except KeyError:
      self.logger.warning('No locations found in sink. Using Unknown Location.')
      return {'8d6c993e-c2cc-11de-8d13-0010c6dffd0f': 'Unknown Location'}

  def _upload_resource(self, resource: str, data: Dict[str, str]):
    """Used to POST when OpenMRS is the target sink."""
    self.fhir_client.post_single_resource(resource, data)
    return self.fhir_client.response['id']

  def upload_openmrs_bundle(self, json_file: pathlib.Path,
      locations: Dict[str, str]):
    """Uploads FHIR Bundle to OpenMRS via Patients, Encounters, Observations.

    As the OpenMRS FHIR Module does not support uploading Bundle transactions,
    the Bundle is uploaded in 3 steps. First the Patient resource is uploaded,
    then the encounters, then the observations. Before uploading each resource,
    we have to manipulate the JSON for that resource into a form OpenMRS will
    accept.

    As OpenMRS does not support PUT requests, each time we POST a resource, a
    new ID for that resource is generated. This means we need to track the new
    id for each resource. Some resources depend on the other resources' new id.
    For example, before POSTing Encounter resource, we need to update it with
    the new Patient id generated by OpenMRS for the Encounter upload to work.

    Args:
      json_file: The JSON file that needs to be uploaded.
      locations: dictionary of location_id/location_name
    """

    try:
      each_bundle = _convert_to_bundle(json_file)
      each_bundle.extract_resources()
      self.logger.info('Uploading %s' % each_bundle.file_name)

      each_bundle.openmrs_patient.openmrs_convert()
      each_bundle.openmrs_patient.base.new_id = self._upload_resource(
          resource='Patient', data=each_bundle.openmrs_patient.base.json)

      self.logger.debug('New Patient ID is %s' %
                        each_bundle.openmrs_patient.base.new_id)

      for openmrs_encounter in each_bundle.openmrs_encounters:
        location = random.choice(list(locations.items()))
        openmrs_encounter.openmrs_convert(
            each_bundle.openmrs_patient.base.new_id, location)
        openmrs_encounter.base.new_id = self._upload_resource(
            resource='Encounter', data=openmrs_encounter.base.json)

      for openmrs_observation in each_bundle.openmrs_observations:
        openmrs_observation.openmrs_convert(
            each_bundle.openmrs_patient.base.new_id,
            each_bundle.openmrs_encounters)
        openmrs_observation.new_id = self._upload_resource(
            resource='Observation', data=openmrs_observation.base.json)

      self.logger.info('Successfully uploaded %s' % each_bundle.file_name)
      each_bundle.save_mapping()

    except ValueError:
      self.logger.error('Error uploading %s.\n%s' %
                        (json_file.as_posix(), traceback.format_exc()))

  def upload_bundle(self, json_file: pathlib.PosixPath):
    """Upload bundle to a FHIR Server via a POST request."""
    try:
      each_bundle = _convert_to_bundle(json_file)
      self.logger.info('Uploading %s' % each_bundle.file_name)
      self.fhir_client.post_bundle(data=each_bundle.bundle_dict)
      self.logger.info('Successfully uploaded %s' % each_bundle.file_name)

    except ValueError:
      self.logger.error('Error uploading %s.\n%s' %
                        (json_file.as_posix(), traceback.format_exc()))


def _convert_to_bundle(json_file: pathlib.Path) -> bundle.Bundle:
  """Loads content of the given file to create a Bundle object.

  Args:
   json_file: A JSON file that need to be converted to a Bundle resource.

  Returns:
    Bundle object
  """
  with open(json_file) as f:
    data = json.loads(f.read())
    return bundle.Bundle(json_file, data)


