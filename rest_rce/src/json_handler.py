import json
import os
from fastapi import HTTPException


class JsonHandler:
	def __init__(self, file_path):
		self.file_path = file_path

	def validate_file(self):
		"""Validate the JSON file at the given path."""
		if not self.file_path.endswith('.json'):
			raise ValueError(f'Invalid file type: {self.file_path}. Expected a .json file.')

		if not os.path.exists(self.file_path):
			raise FileNotFoundError(f"The file '{self.file_path}' does not exist.")

		try:
			with open(self.file_path) as file:
				json.load(file)
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid JSON syntax in file '{self.file_path}': {e}") from e

		# return a success message if nothing failed
		return f"File with path '{self.file_path}' is a valid JSON file."

	def extract_values(self):
		"""Extract and validate essential fields from the JSON file."""
		with open(self.file_path, "r") as f:
			config_data = json.load(f)
		# Extract and validate essential fields
		enable_command_script = config_data.get(
			"enableCommandScriptWindows" if os.name == "nt" else "enableCommandScriptLinux", False)
		command_script = config_data.get(
			"commandScriptWindows" if os.name == "nt" else "commandScriptLinux", "")
		set_tool_dir = config_data.get("setToolDirAsWorkingDir", False)
		tool_directory = config_data.get("launchSettings", [])[0].get("toolDirectory", "")
		inputs = config_data.get("inputs", [])

		if not command_script:
			raise HTTPException(status_code=400, detail="No command script specified in the configuration file.")
		if not enable_command_script:
			raise HTTPException(status_code=400,
								detail="Command script execution is disabled in the configuration file.")
		if not tool_directory:
			raise HTTPException(status_code=400, detail="No tool directory specified in the configuration file.")
		if not inputs:
			raise HTTPException(status_code=400, detail="No inputs specified in the configuration file.")

		return command_script, set_tool_dir, tool_directory, inputs
