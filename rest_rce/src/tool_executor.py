import os
import subprocess

from json_handler import JsonHandler


class ToolExecutor:
	def __init__(self, tool_config, inputs, logger):
		self.tool_config = tool_config
		self.inputs = inputs
		self.logger = logger

	@staticmethod
	def validate_input_datatypes(value, config_datatype):
		"""Validate a single input's data type."""
		incoming_dtype = type(value).__name__
		if config_datatype == 'string':
			if not isinstance(value, str):
				raise ValueError(f'Expected String, but got {incoming_dtype}: {value}')
		elif config_datatype == 'integer':
			if not isinstance(value, int):
				raise ValueError(f'Expected Integer, but got {incoming_dtype}: {value}')
		elif config_datatype == 'float':
			if not isinstance(value, (float, int)):
				raise ValueError(f'Expected Float, but got {incoming_dtype}: {value}')
		elif config_datatype == 'boolean':
			if not isinstance(value, bool):
				raise ValueError(f'Expected Boolean, but got {incoming_dtype}: {value}')
		elif config_datatype in ['file', 'filereference']:
			if not isinstance(value, str) or not value.endswith(('.txt', '.csv', '.json', '.xml')):
				raise ValueError(f'Expected File (path string), but got {incoming_dtype}: {value}')
		elif config_datatype in ['array', 'list']:
			if not isinstance(value, list):
				raise ValueError(f'Expected Array/List, but got {incoming_dtype}: {value}')
		elif config_datatype == 'map':
			if not isinstance(value, dict):
				raise ValueError(f'Expected Map (key-value), but got {incoming_dtype}: {value}')
		else:
			raise ValueError(f'Unsupported endpoint data type: {config_datatype}')

	def validate_inputs(self):
		"""Validate the input values given in the post request with the tool configuration."""
		provided_inputs = self.inputs
		inputs_config = self.tool_config.get('inputs', [])
		# Check for unexpected inputs
		expected_input_names = {inp['endpointName'] for inp in inputs_config}
		unexpected_inputs = [key for key in provided_inputs if key not in expected_input_names]
		if len(unexpected_inputs) > 0:
			raise ValueError(f'Post request containing unexpected inputs: {unexpected_inputs}')
		for inp in inputs_config:
			endpoint_name = inp.get('endpointName')
			endpoint_datatype = inp.get('endpointDataType').lower()
			# Check for missing required inputs
			if endpoint_name not in provided_inputs:
				raise ValueError(f'Post request missing required input: {endpoint_name}.')
			value = provided_inputs[endpoint_name]
			# Check for empty values
			if value is None:
				raise ValueError(f'Input value for {endpoint_name} is empty.')
			# Validate the data type
			self.validate_input_datatypes(value, endpoint_datatype)

	def execute_tool(self, tool_config):
		"""Execute the tool with the provided inputs."""
		# Use JsonHandler to extract values
		json_handler = JsonHandler()
		command_script, set_tool_dir, tool_directory, inputs = json_handler.extract_values(
			tool_config
		)
		# Replace the input placeholders in the command script
		for key, value in self.inputs.items():
			command_script = command_script.replace(f'${{in:{key}}}', str(value))
		# Change working directory if required
		start_working_dir = os.getcwd()
		if set_tool_dir and tool_directory:
			os.chdir(tool_directory)
			self.logger.info(f'Working directory changed to {tool_directory}.')
		# Execute the command script
		self.logger.info(f'Executing command script: {command_script}')
		process = subprocess.run(command_script, shell=True, capture_output=True, text=True)
		stdout = process.stdout
		stderr = process.stderr
		return_code = process.returncode
		# Restore working directory
		if set_tool_dir and tool_directory:
			os.chdir(start_working_dir)

		return return_code, stdout, stderr, tool_directory, command_script
