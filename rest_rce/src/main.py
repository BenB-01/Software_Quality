import asyncio
import datetime
import logging
import multiprocessing
import sys
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.tool_executor import ToolExecutor
from rest_rce.src.utils import parse_arguments, set_up_logger

# Context variable to store request ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Global variables to store tool configuration and status of processes
tool_config = {}
execution_status = {}

# Set up logger
logger = set_up_logger(request_id_var)

# Parse CLI arguments before starting FastAPI
config_file_path, tool_timeout, request_limit = parse_arguments()


# Pydantic model for input values
class InputValues(BaseModel):
	inputs: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Initialize the configuration from the JSON file passed via command-line argument."""
	global tool_config, tool_timeout, request_limit

	try:
		handler = JsonHandler(logger, config_file_path)
		handler.validate_file()
		handler.validate_schema()
		handler.validate_essential_fields()
		config_file = handler.read_file()
		tool_config.update(config_file)
		tool_name = tool_config.get('toolName')
		logger.info(f'Tool configuration of tool "{tool_name}" loaded successfully.')
	except Exception as e:
		logger.error(e)
		sys.exit(1)

	yield

	# Clean up resources
	tool_config.clear()
	logger.info('Tool configuration cleared.')

	# Ensure logs are written to the file
	logger.info(f'Shutting down the tool "{tool_name}". Logs written to tool_execution.log.')
	for handler in logger.handlers:
		if isinstance(handler, logging.FileHandler):
			handler.close()


app = FastAPI(lifespan=lifespan)


@app.middleware('http')
async def log_requests(request: Request, call_next):
	"""Middleware to log incoming requests and responses with a unique request ID."""
	request_id = str(uuid.uuid4().hex[:8])
	request_id_var.set(request_id)

	logger.info(f'Incoming request: {request.method} {request.url}')
	response = await call_next(request)
	logger.info(f'Response status: {response.status_code}')

	return response


@app.get('/')
def read_root():
	logger.info('Root endpoint accessed.')
	return {'message': 'API is running. Tool configuration loaded.', 'configuration': tool_config}


@app.get('/running-processes/')
def get_running_processes():
	global execution_status
	running_processes = [
		(key, value) for key, value in execution_status.items() if value.get('status') == 'running'
	]
	logger.info(f'Running processes: {running_processes}.')
	return running_processes


@app.post('/execute-tool/')
async def execute_tool(input_values: InputValues):
	global tool_config, tool_timeout, request_limit

	running_processes = get_running_processes()
	logger.info(f'Number of parallel running processes: {len(running_processes)}.')
	if request_limit is not None and len(running_processes) >= request_limit:
		logger.error(f'Post request denied because request limit of {request_limit} is reached.')
		logger.info("Running processes can be seen at '/running-processes/'.")
		raise HTTPException(status_code=429, detail='Request limit reached.')

	if not tool_config:
		logger.error('Tool configuration is not loaded.')
		raise HTTPException(status_code=400, detail='Tool configuration is not loaded.')

	# Add request ID to execution status dictionary
	execution_id = request_id_var.get()
	execution_status[execution_id] = {'status': 'running', 'started_at': datetime.datetime.now()}

	def run_execution():
		"""Execute the tool and update execution status."""
		try:
			executor = ToolExecutor(tool_config, input_values.inputs, logger, tool_timeout)
			executor.validate_inputs()

			return_code, stdout, stderr, tool_directory, command_script, output_vars = (
				executor.execute_tool()
			)

			if return_code != 0:
				execution_status[execution_id]['status'] = 'failed'
				execution_status[execution_id]['stderr'] = stderr
				if return_code == -1:
					raise HTTPException(status_code=408, detail=f'{stderr}')
				if return_code == -2:
					raise HTTPException(status_code=403, detail=f'{stderr}')

			execution_status[execution_id]['status'] = 'completed'
			execution_status[execution_id].update(
				{
					'stdout': stdout,
					'tool_directory': tool_directory,
					'command': command_script,
					'output_variables': output_vars,
				}
			)

			return {
				'execution_id': execution_id,
				'command': command_script,
				'tool_directory': tool_directory,
				'stdout': stdout,
				'output_variables': output_vars,
			}

		except Exception as e:
			logger.error(f'Error during tool execution: {e}')
			execution_status[execution_id]['status'] = 'failed'
			execution_status[execution_id]['error'] = str(e)
			raise HTTPException(status_code=500, detail=str(e)) from e

	# Ensure to properly await the function to get the result
	result = await asyncio.to_thread(run_execution)

	return result


def main():
	"""Entry point for CLI execution."""
	logger.info(f'Starting the tool with configuration file: {config_file_path}')
	if tool_timeout:
		logger.info(f'Tool timeout set to {tool_timeout} minutes.')
	else:
		logger.info('No timeout set for tool execution.')
	logger.info(f'Request limit set to {request_limit} parallel processes.')

	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)


if __name__ == '__main__':
	main()
