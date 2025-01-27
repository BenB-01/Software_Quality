import json
import os
import re

import requests
from fastapi import HTTPException

from rest_rce.src.constants import (
	CS_L,
	CS_W,
	ENABLE_CS_L,
	ENABLE_CS_W,
	INPUTS,
	LAUNCH_SETTINGS,
	OUTPUTS,
	TOOL_DIR,
)


class JsonHandler:
	def __init__(
		self,
		logger,
		file_path=None,
	):
		self.logger = logger
		self.file_path = file_path
		self.possible_keys = self.fetch_config_file_keys()

	def fetch_config_file_keys(self):
		"""Get all possible keys from the RCE GitHub repository which can be in the config file."""
		raw_urls = [
			'https://raw.githubusercontent.com/rcenvironment/rce/master/de.rcenvironment.core.component.integration/'
			'src/main/java/de/rcenvironment/core/component/integration/IntegrationConstants.java',
			'https://raw.githubusercontent.com/rcenvironment/rce/master/de.rcenvironment.core.component.integration/'
			'src/main/java/de/rcenvironment/core/component/integration/ToolIntegrationConstants.java',
		]
		all_keys = []
		# Fetch the file content from GitHub
		for url in raw_urls:
			try:
				response = requests.get(url)
				response.raise_for_status()  # Raise an exception for HTTP errors
				java_code = response.text
				# Find all matches in the Java code
				pattern = r'public static final String (KEY_\w+) = "(.*?)";'
				matches = re.findall(pattern, java_code)
				# Extract the constant values into a list
				key_values = [value for _, value in matches]
				all_keys.extend(key_values)
			except requests.RequestException as e:
				self.logger.error(f'Error fetching file from {url}: {e}')
				return []

		return all_keys

	def read_file(self):
		"""Read the JSON file at the given path."""
		with open(self.file_path) as file:
			json_data = json.load(file)
		return json_data

	def validate_schema(self):
		"""Validate if the schema of the JSON file matches the keys defined in the RCE repo."""
		json_data = self.read_file()
		invalid_keys = [key for key in json_data if key not in self.possible_keys]
		if invalid_keys:
			raise ValueError(
				f'The configuration file contains invalid keys: {invalid_keys}. '
				f'Allowed keys are: {self.possible_keys}'
			)

	def validate_file(self):
		"""Validate the JSON file at the given path, return the JSON data if valid."""
		if not self.file_path.endswith('.json'):
			raise ValueError(f'Invalid file type: {self.file_path}. Expected a .json file.')
		if not os.path.exists(self.file_path):
			raise FileNotFoundError(f"The file '{self.file_path}' does not exist.")
		try:
			json_data = self.read_file()
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid JSON syntax in file '{self.file_path}': {e}") from e

		return json_data

	def validate_essential_fields(self, test_json_data=None):
		"""Validate if the essential fields are present with an associated value."""
		# Can either load the JSON data from the file or use other provided data (for testing)
		json_data = self.read_file() if test_json_data is None else test_json_data

		field_command_script = CS_W if os.name == 'nt' else CS_L
		field_enable_cs = ENABLE_CS_W if os.name == 'nt' else ENABLE_CS_L
		key_mapping = {
			field_command_script: 'Command script',
			field_enable_cs: 'Enable command script',
			LAUNCH_SETTINGS: 'Launch settings',
			OUTPUTS: 'Outputs',
			INPUTS: 'Inputs',
		}

		# Check if essential fields are present or not an empty string
		for key, description in key_mapping.items():
			if key not in json_data or not json_data[key]:
				if key == field_enable_cs:
					message = (
						f'Command script execution is disabled in the configuration file. '
						f'Set field {field_enable_cs} to True.'
					)
				else:
					message = (
						f'{description} not specified in the configuration file. '
						f'Please add the key "{key}".'
					)
				raise HTTPException(status_code=400, detail=message)

		# Check if tool directory is in launch settings
		launch_settings = json_data.get(LAUNCH_SETTINGS)
		if TOOL_DIR not in launch_settings[0] or not launch_settings[0][TOOL_DIR]:
			message = (
				f'Tool directory not specified in the configuration file. '
				f"Specify directory with key '{TOOL_DIR}' in launch settings."
			)
			raise HTTPException(status_code=400, detail=message)
