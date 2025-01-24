import os
import re
import subprocess

from constants import (
	CS_L,
	CS_W,
	LAUNCH_SETTINGS,
	POST_S,
	PRE_S,
	SET_AS_WORKING_DIR,
	TOOL_DIR,
)


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

	def validate_outputs(self, output_vars):
		"""Validate the output variables with the tool configuration."""
		pass

	def execute_python_script(self, script, tool_directory, output_vars=None):
		"""Execute a pre-/post-script with placeholders for directories and output variables."""
		# Replace ${dir:tool} with the tool directory
		script = script.replace('${dir:tool}', tool_directory)

		output_matches = re.findall(r'\$\{out:(\w+)\}', script)
		for match in output_matches:
			# Replace the output placeholder with a variable name
			script = script.replace(f'${{out:{match}}}', f"output_vars['{match}']")

		# Prepare the execution environment
		local_vars = {'output_vars': output_vars}

		# Execute the dynamically generated script
		try:
			exec(script, {}, local_vars)
		except Exception as e:
			self.logger.error(f'Error while executing script: {script}. Error: {e}')

		return output_vars

	def execute_tool(self):
		"""Execute the tool with the provided inputs."""
		field_command_script = CS_W if os.name == 'nt' else CS_L
		command_script = self.tool_config.get(field_command_script, '')
		set_tool_dir = self.tool_config.get(SET_AS_WORKING_DIR, '')
		launch_settings = self.tool_config.get(LAUNCH_SETTINGS, [])
		tool_directory = launch_settings[0].get(TOOL_DIR, '')
		pre_script = self.tool_config.get(PRE_S, '')
		post_script = self.tool_config.get(POST_S, '')

		# Replace the input placeholders in the command script
		for key, value in self.inputs.items():
			command_script = command_script.replace(f'${{in:{key}}}', str(value))

		# Change working directory if required
		start_working_dir = os.getcwd()
		if set_tool_dir and tool_directory:
			os.chdir(tool_directory)
			self.logger.info(f'Working directory changed to {tool_directory}.')

		# Execute the pre-script if defined
		output_vars = {}
		if pre_script:
			self.logger.info(f'Executing pre-script: {pre_script}')
			self.execute_python_script(pre_script, tool_directory, output_vars)

		# Execute the command script
		self.logger.info(f'Executing command script: {command_script}')
		process = subprocess.run(command_script, shell=True, capture_output=True, text=True)
		stdout = process.stdout
		stderr = process.stderr
		return_code = process.returncode

		# Execute the post-script if defined
		if post_script:
			cleaned_post_script = stdout.replace('\n', ' | ')
			self.logger.info(f'Executing post-script: {cleaned_post_script}.')
			output_vars = self.execute_python_script(post_script, tool_directory, output_vars)
			self.logger.info(f'Outputs from Post-script: {output_vars}')

		# Restore working directory
		if set_tool_dir and tool_directory:
			os.chdir(start_working_dir)

		return return_code, stdout, stderr, tool_directory, command_script, output_vars
