import logging
import multiprocessing
import os
import subprocess
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from json_handler import JsonHandler
from pydantic import BaseModel

# Set up logging
logging.basicConfig(
	level=logging.INFO,
	format='%(levelname)s: %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Global variable to store tool configuration
tool_config = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Initialize the configuration from the JSON file passed via command-line argument."""
	global tool_config

	if len(sys.argv) < 2:
		logger.error(
			'No configuration file provided. Start the API with: `python app.py config.json`'
		)
		sys.exit(1)

	config_file_path = sys.argv[1]

	try:
		handler = JsonHandler(config_file_path)
		config_file = handler.validate_file()
		tool_config.update(config_file)
		logger.info('Tool configuration loaded successfully.')
	except Exception as e:
		logger.error(e)
		sys.exit(1)

	yield  # Keep the application running

	# Clean up resources
	tool_config.clear()
	logger.info('Tool configuration cleared.')


app = FastAPI(lifespan=lifespan)


class InputValues(BaseModel):
	inputs: dict


@app.get('/')
def read_root():
	message = f'API is running. Tool configuration loaded. \nConfiguration: {tool_config}'
	return message


@app.post('/execute-tool/')
def execute_tool(input_values: InputValues):
	"""Endpoint to execute a tool using the preloaded configuration and provided inputs."""
	global tool_config
	start_working_dir = os.getcwd()
	set_tool_dir, tool_directory = False, ''

	if not tool_config:
		raise HTTPException(status_code=500, detail='Tool configuration is not loaded.')

	try:
		# Use JsonHandler to extract values
		json_handler = JsonHandler()
		command_script, set_tool_dir, tool_directory, inputs = json_handler.extract_values(
			tool_config
		)

		# Replace placeholders with input values
		provided_inputs = input_values.inputs
		for inp in inputs:
			endpoint_name = inp.get('endpointName')
			if endpoint_name not in provided_inputs:
				raise HTTPException(
					status_code=400, detail=f'Missing required input: {endpoint_name}'
				)
			value = provided_inputs[endpoint_name]
			command_script = command_script.replace(f'${{in:{endpoint_name}}}', str(value))

		# Change working directory if required
		if set_tool_dir and tool_directory:
			os.chdir(tool_directory)
			logger.info(f'Working directory changed to {tool_directory}.')

		# Execute the tool command
		process = subprocess.run(command_script, shell=True, capture_output=True, text=True)
		stdout = process.stdout
		stderr = process.stderr

		if process.returncode != 0:
			raise HTTPException(status_code=500, detail=f'Tool execution failed: {stderr}')

		# Return the results
		return {
			'stdout': stdout,
			'tool_directory': tool_directory,
			'command': command_script,
		}

	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e)) from e

	finally:
		# Restore working directory
		if set_tool_dir and tool_directory:
			os.chdir(start_working_dir)


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)
