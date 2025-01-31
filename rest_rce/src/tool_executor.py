import os
import re
import subprocess

from rest_rce.src.constants import (
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
		elif config_datatype in ['file', 'filereference', 'directory']:
			if not isinstance(value, str):
				raise ValueError(f'Expected path string, but got {incoming_dtype}: {value}')
			file_or_dir_pattern = re.compile(r'^(.*[/\\])?[\w-]+(\.(txt|csv|json|xml))?$')
			if not file_or_dir_pattern.match(value):
				raise ValueError(f'Invalid file or directory path: {value}')
		elif config_datatype in ['array', 'list']:
			if not isinstance(value, list):
				raise ValueError(f'Expected Array/List, but got {incoming_dtype}: {value}')
		elif config_datatype == 'map':
			if not isinstance(value, dict):
				raise ValueError(f'Expected Map (key-value), but got {incoming_dtype}: {value}')
		else:
			raise ValueError(f'Unsupported endpoint data type: {config_datatype}')

	@staticmethod
	def find_project_directory(start_dir):
		"""Recursively search for a pyproject.toml file starting from the given directory."""
		current_dir = start_dir
		while current_dir:
			if os.path.exists(os.path.join(current_dir, 'pyproject.toml')):
				return current_dir
			parent_dir = os.path.dirname(current_dir)
			if parent_dir == current_dir:  # Reached the root directory
				break
			current_dir = parent_dir
		return None

	def validate_inputs(self):
		"""Validate the input values given in the post request with the tool configuration."""
		provided_inputs = self.inputs
		inputs_config = self.tool_config.get('inputs', [])

		# Check for unexpected inputs
		expected_inputs = {inp['endpointName'] for inp in inputs_config}
		unexpected_inputs = [key for key in provided_inputs if key not in expected_inputs]
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
		output_config = self.tool_config.get('outputs', [])

		# Check for unexpected outputs
		expected_outputs = {out['endpointName'] for out in output_config}
		unexpected_outputs = [
			key for key, value in output_vars.items() if key not in expected_outputs
		]
		if len(unexpected_outputs) > 0:
			msg = f'Tool returned outputs not defined in the config file: {unexpected_outputs}'
			raise ValueError(msg)

		for key, value in output_vars.items():
			# Check for empty values
			if value is None:
				raise ValueError(f'Output value for {key} is empty.')
			# Validate the data type
			endpoint_datatype = output_config[0].get('endpointDataType').lower()
			self.validate_input_datatypes(value, endpoint_datatype)

	def set_execute_permission(self, tool_directory, command_script):
		"""Ensure that a script file used to execute the tool in Linux has execute permissions."""
		script_path = os.path.join(tool_directory, command_script.split()[0])
		if not os.access(script_path, os.X_OK):
			self.logger.info(f'No permission to execute: {script_path}. Attempting to fix...')
			try:
				os.chmod(script_path, 0o755)
				self.logger.info(f'Execute permission set successfully for {script_path}')
			except Exception as e:
				self.logger.error(f'Failed to set execute permission: {e}')

	def execute_python_script(self, script, tool_dir, project_dir, output_vars=None):
		"""Execute a pre-/post-script with placeholders for directories and output variables."""
		# Replace ${dir:tool} with the tool directory
		script = script.replace('${dir:tool}', tool_dir)

		output_matches = re.findall(r'\$\{out:(\w+)\}', script)
		for match in output_matches:
			# Replace the output placeholder with a variable name
			script = script.replace(f'${{out:{match}}}', f"output_vars['{match}']")

		# Prepare the execution environment
		local_vars = {'output_vars': output_vars}

		# Track installed dependencies to clean up later
		installed_dependencies = set()

		original_cwd = os.getcwd()
		try:
			# Change working directory to project directory
			os.chdir(project_dir)

			while True:
				try:
					# Execute the dynamically generated script
					exec(script, {}, local_vars)
					break  # If execution succeeds, exit the loop
				except ImportError as e:
					missing_module = str(e).split("'")[1]
					self.logger.warning(
						f'Missing dependency detected: {missing_module}. Attempting to install it.'
					)

					# Add missing dependency
					try:
						subprocess.run(['poetry', 'add', missing_module], check=True)
						installed_dependencies.add(missing_module)
						self.logger.info(
							f'Missing dependency {missing_module} successfully installed. '
							f'Trying to rerun the script.'
						)
					except subprocess.CalledProcessError as install_error:
						self.logger.error(
							f'Failed to install missing dependency {missing_module}. '
							f'Error: {install_error}'
						)
						raise install_error  # Reraise if installation fails
				except Exception as e:
					self.logger.error(f'Error while executing script: {e}')
					raise e  # Reraise for unexpected errors

			# Cleanup: Remove installed dependencies
			for dependency in installed_dependencies:
				try:
					subprocess.run(['poetry', 'remove', dependency], check=True)
					self.logger.info(f'Cleaned up dependency: {dependency}')
				except subprocess.CalledProcessError as cleanup_error:
					self.logger.warning(
						f'Failed to clean up dependency {dependency}. Error: {cleanup_error}'
					)

		finally:
			# Restore original working directory
			os.chdir(original_cwd)

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

		# Find the project directory with pyproject.toml
		start_working_dir = os.getcwd()
		project_directory = self.find_project_directory(start_working_dir)
		if not project_directory:
			self.logger.error(
				"Could not find pyproject.toml. Ensure you're in the correct project environment."
			)
			raise FileNotFoundError('pyproject.toml not found in any parent directories.')

		# Execute the pre-script if defined
		output_vars = {}
		if pre_script:
			self.logger.info(f'Executing pre-script: \n{pre_script}')
			self.execute_python_script(pre_script, tool_directory, project_directory, output_vars)

		# Change working directory if required
		tool_directory = tool_directory if set_tool_dir and tool_directory else start_working_dir

		# Check execute permissions for Linux
		if os.name != 'nt':
			self.set_execute_permission(tool_directory, command_script)

		# Execute the command script
		self.logger.info(f'Executing command script: {command_script}')
		try:
			process = subprocess.run(
				command_script, shell=True, capture_output=True, text=True, cwd=tool_directory
			)
			stdout = process.stdout
			stderr = process.stderr
			return_code = process.returncode
		except PermissionError:
			self.logger.error(f'Permission denied when executing {command_script}')
			stderr = f'Permission denied: {command_script}'
			return -1, '', stderr, tool_directory, command_script, {}

		# Execute the post-script if defined
		if post_script:
			self.logger.info(f'Executing post-script: \n{post_script}.')
			output_vars = self.execute_python_script(
				post_script, tool_directory, project_directory, output_vars
			)
			# Validate outputs with expected outputs from config file
			self.validate_outputs(output_vars)
			self.logger.info(f'Outputs from Post-script: {output_vars}')

		# Restore working directory
		if set_tool_dir and tool_directory:
			os.chdir(start_working_dir)

		return return_code, stdout, stderr, tool_directory, command_script, output_vars
