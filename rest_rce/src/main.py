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

# Context variable to store request ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

execution_status = {}


def set_up_logger():
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(levelname)s - [Request ID: %(request_id)s] - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S',
	)

	class ContextFilter(logging.Filter):
		"""Logging filter to add request_id to log records."""

		def filter(self, record):
			request_id = request_id_var.get()
			record.request_id = request_id if request_id else 'SYSTEM'
			return True

	log_file_handler = logging.FileHandler('tool_execution.log')
	log_file_handler.setFormatter(formatter)
	log_file_handler.addFilter(ContextFilter())

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	console_handler.addFilter(ContextFilter())

	logger.addHandler(log_file_handler)
	logger.addHandler(console_handler)

	return logger


logger = set_up_logger()

# Global variables to store tool configuration
tool_config = {}
tool_timeout = None


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Initialize the configuration from the JSON file passed via command-line argument."""
	global tool_config, tool_timeout

	if len(sys.argv) < 2:
		logger.error(
			'No configuration file provided. Start the API with: `python app.py <config.json>`'
		)
		sys.exit(1)

	config_file_path = sys.argv[1]
	tool_timeout = float(sys.argv[2]) if len(sys.argv) > 2 else None

	try:
		handler = JsonHandler(logger, config_file_path)
		handler.validate_file()
		handler.validate_schema()
		handler.validate_essential_fields()
		config_file = handler.read_file()
		tool_config.update(config_file)
		tool_name = tool_config.get('toolName')
		logger.info(f'Tool configuration of tool {tool_name} loaded successfully.')
		if tool_timeout is not None:
			logger.info(f'Tool timeout set to : {tool_timeout} minutes.')
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
	return running_processes


@app.post('/execute-tool/')
async def execute_tool(input_values: InputValues):
	global tool_config, tool_timeout

	if not tool_config:
		logger.error('Tool configuration is not loaded.')
		raise HTTPException(status_code=500, detail='Tool configuration is not loaded.')

	# Retrieve the request ID from context variable
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
				'stdout': stdout,
				'tool_directory': tool_directory,
				'command': command_script,
				'output_variables': output_vars,
			}

		except Exception as e:
			logger.error(f'Error during tool execution: {e}')
			execution_status[execution_id]['status'] = 'failed'
			execution_status[execution_id]['error'] = str(e)
			raise HTTPException(status_code=500, detail=str(e)) from e

	# Ensure to properly await the function to get the result and not a coroutine
	result = await asyncio.to_thread(run_execution)

	return result


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)
