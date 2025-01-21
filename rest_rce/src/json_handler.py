import json
import os
import re

import requests
from fastapi import HTTPException


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

	def validate_schema(self, json_data):
		"""Validate if the schema of the JSON file matches the keys defined in the RCE repo."""
		invalid_keys = [key for key in json_data if key not in self.possible_keys]
		if invalid_keys:
			raise ValueError(
				f'The configuration file contains invalid keys: {invalid_keys}. '
				f'Allowed keys are: {self.possible_keys}'
			)

	def validate_file(self):
		"""Validate the JSON file at the given path."""
		if not self.file_path.endswith('.json'):
			raise ValueError(f'Invalid file type: {self.file_path}. Expected a .json file.')
		if not os.path.exists(self.file_path):
			raise FileNotFoundError(f"The file '{self.file_path}' does not exist.")
		try:
			with open(self.file_path) as file:
				json_data = json.load(file)
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid JSON syntax in file '{self.file_path}': {e}") from e
		self.validate_schema(json_data)

		return json_data

	def extract_values(self, file):
		"""Extract and validate essential fields from the JSON file."""
		# Extract and validate essential fields
		enable_command_script = file.get(
			'enableCommandScriptWindows' if os.name == 'nt' else 'enableCommandScriptLinux', False
		)
		command_script = file.get(
			'commandScriptWindows' if os.name == 'nt' else 'commandScriptLinux', ''
		)
		set_tool_dir = file.get('setToolDirAsWorkingDir', False)
		tool_directory = file.get('launchSettings', [])[0].get('toolDirectory', '')
		inputs = file.get('inputs', [])

		if not command_script:
			raise HTTPException(
				status_code=400, detail='No command script specified in the configuration file.'
			)
		if not enable_command_script:
			raise HTTPException(
				status_code=400,
				detail='Command script execution is disabled in configuration file.',
			)
		if not tool_directory:
			raise HTTPException(
				status_code=400, detail='No tool directory specified in the configuration file.'
			)
		if not inputs:
			raise HTTPException(
				status_code=400, detail='No inputs specified in the configuration file.'
			)

		return command_script, set_tool_dir, tool_directory, inputs
