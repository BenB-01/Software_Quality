import json
import os

from fastapi import HTTPException


class JsonHandler:
	def __init__(self, file_path=None):
		self.file_path = file_path

	def validate_file(self):
		"""Validate the JSON file at the given path."""
		if not self.file_path.endswith('.json'):
			raise ValueError(f'Invalid file type: {self.file_path}. Expected a .json file.')

		if not os.path.exists(self.file_path):
			raise FileNotFoundError(f"The file '{self.file_path}' does not exist.")

		try:
			with open(self.file_path) as file:
				file = json.load(file)
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid JSON syntax in file '{self.file_path}': {e}") from e

		return file

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
