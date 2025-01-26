import logging
import multiprocessing
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.tool_executor import ToolExecutor


def set_up_logger():
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
	)

	log_file_handler = logging.FileHandler('tool_execution.log')
	log_file_handler.setFormatter(formatter)
	logger.addHandler(log_file_handler)

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)

	return logger


logger = set_up_logger()

# Global variable to store tool configuration
tool_config = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Initialize the configuration from the JSON file passed via command-line argument."""
	global tool_config

	if len(sys.argv) < 2:
		logger.error(
			'No configuration file provided. Start the API with: `python app.py <config.json>`'
		)
		sys.exit(1)

	config_file_path = sys.argv[1]

	try:
		handler = JsonHandler(logger, config_file_path)
		handler.validate_file()
		handler.validate_schema()
		handler.validate_essential_fields()
		config_file = handler.read_file()
		tool_config.update(config_file)
		tool_name = tool_config.get('toolName')
		logger.info(f'Tool configuration of tool {tool_name} loaded successfully.')
	except Exception as e:
		logger.error(e)
		sys.exit(1)

	yield

	# Clean up resources
	tool_config.clear()
	logger.info('Tool configuration cleared.')

	# Ensure logs are written to the file
	logger.info('Shutting down the tool. Logs written to tool_execution.log.')
	for handler in logger.handlers:
		if isinstance(handler, logging.FileHandler):
			handler.close()


app = FastAPI(lifespan=lifespan)


class InputValues(BaseModel):
	inputs: dict


@app.middleware('http')
async def log_requests(request: Request, call_next):
	"""Log incoming requests and responses."""
	logger.info(f'Incoming request: {request.method} {request.url}')
	response = await call_next(request)
	logger.info(f'Response status: {response.status_code}')
	return response


@app.get('/')
def read_root():
	message = f'API is running. Tool configuration loaded. \nConfiguration: {tool_config}'
	logger.info('Root endpoint accessed.')
	return message


@app.post('/execute-tool/')
def execute_tool(input_values: InputValues):
	"""Endpoint to execute a tool using the preloaded configuration and provided inputs."""
	global tool_config

	if not tool_config:
		logger.error('Tool configuration is not loaded.')
		raise HTTPException(status_code=500, detail='Tool configuration is not loaded.')

	try:
		# Validate the input values
		executor = ToolExecutor(tool_config, input_values.inputs, logger)
		executor.validate_inputs()
		# Execute the tool with the provided inputs
		return_code, stdout, stderr, tool_directory, command_script, output_vars = (
			executor.execute_tool()
		)

		if return_code != 0:
			logger.error(f'Tool execution failed with stderr: {stderr}')
			raise HTTPException(status_code=500, detail=f'Tool execution failed: {stderr}')

		# Return the results
		cleaned_stdout = stdout.replace('\n', ' | ')
		logger.info(f'Tool executed successfully with stdout: {cleaned_stdout}')
		return {
			'stdout': stdout,
			'tool_directory': tool_directory,
			'command': command_script,
			'output_variables': output_vars,
		}

	except Exception as e:
		logger.error(f'Error during tool execution: {e}')
		raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)
