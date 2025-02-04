import asyncio
import os
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from rest_rce.src.main import app, tool_config
from rest_rce.src.utils import assert_output_values
from rest_rce.test.shared.test_main_shared import mock_get_running_processes  # noqa

client = TestClient(app)
request_limit = 10


@pytest.fixture
def mock_tool_config():
	tool_config.update(
		{
			'enableCommandScriptWindows': True,
			'commandScriptWindows': 'root.exe ${in:x}',
			'setToolDirAsWorkingDir': True,
			'launchSettings': [{'toolDirectory': 'rest_rce/test/tools/root/'}],
			'inputs': [{'endpointName': 'x', 'endpointDataType': 'Float'}],
			'outputs': [{'endpointName': 'root', 'endpointDataType': 'Float'}],
			'postScript': 'file = open("${dir:tool}/result.txt","r")'
			'\r\nroot = file.read()'
			'\r\n${out:root} = float(root)',
			'preScript': 'import time'
			'\r\nimport random'
			'\r\ndelay=random.uniform(1,5)'
			'\r\ntime.sleep(delay)',
		}
	)
	return tool_config


def test_execute_tool_windows(mock_tool_config):
	"""Test execution of the tool in Windows with a single input."""
	test_input = {'inputs': {'x': 4}}
	expected_output = {
		'command': 'root.exe 4',
		'output_variables': {'root': 2.0},
		'stdout': 'Calculating square root...' '\nGot input x = 4\nWrote result 2 to file.\n',
	}

	# Send a synchronous POST request
	response = client.post('/execute-tool/', json=test_input)

	# Verify response
	assert_output_values(response, expected_output)


def test_execute_tool_windows_connection_error_unresolved(mock_tool_config):
	"""Test execution of the tool in Windows, if a connection error cannot be resolved."""
	test_input = {'inputs': {'x': 36}}

	# Send a synchronous POST request
	with patch(
		'rest_rce.src.tool_executor.ToolExecutor.execute_tool',
		side_effect=requests.exceptions.ConnectionError,
	):
		response = client.post('/execute-tool/', json=test_input)

	# Verify response (of unresolved error)
	assert response.status_code == 500


def test_execute_tool_windows_connection_error_resolved(mock_tool_config):
	"""Test execution of the tool in Windows, if a connection error can be resolved."""
	test_input = {'inputs': {'x': 36}}
	expected_output = {
		'command': 'root.exe 36',
		'output_variables': {'root': 6.0},
		'stdout': 'Calculating square root...' '\nGot input x = 36\nWrote result 6 to file.\n',
	}

	# Send a synchronous POST request
	with patch(
		'os.getcwd',
		side_effect=[
			os.getcwd(),  # during execute_tool
			os.getcwd(),  # during execute_python_script (pre-script)
			requests.exceptions.ConnectionError,  # during execute_python_script (post-script)
			os.getcwd(),  # during execute_tool 2
			os.getcwd(),  # during execute_python_script (pre-script)
			os.getcwd(),
		],
	):  # during execute_python_script (post-script)
		response = client.post('/execute-tool/', json=test_input)

	# Verify response
	assert_output_values(response, expected_output)


@pytest.mark.asyncio
async def test_parallel_tool_execution_windows(mock_tool_config):
	"""Test parallel execution of the tool with different inputs."""

	# Define test inputs and expected outputs
	inputs = [4, 16, 64]
	test_inputs = []
	expected_outputs = []
	stdout_template = 'Calculating square root...\nGot input x = {x}\nWrote result {res} to file.\n'

	for x in inputs:
		res = int(x**0.5)
		stdout_success_msg = stdout_template.format(x=x, res=res)
		test_inputs.append({'inputs': {'x': x}})
		expected_outputs.append(
			{
				'command': f'root.exe {x}',
				'output_variables': {'root': res},
				'stdout': stdout_success_msg,
			}
		)

	async def send_request(client, data):
		response = await client.post('/execute-tool/', json=data)
		return response

	# Create an async client for parallel requests
	async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
		tasks = [send_request(ac, data) for data in test_inputs]
		responses = await asyncio.gather(*tasks)

	# Verify responses
	for response, expected_output in zip(responses, expected_outputs):
		assert_output_values(response, expected_output)


def test_execute_tool_under_limit_windows(mock_get_running_processes, mock_tool_config):  # noqa: F811
	"""Test if execute_tool executes requests when request limit is not reached."""
	mock_get_running_processes.return_value = ['task1', 'task2']
	stdout_success_msg = 'Calculating square root...\nGot input x = 4\nWrote result 2 to file.\n'
	expected_output = {
		'command': 'root.exe 4',
		'output_variables': {'root': 2},
		'stdout': stdout_success_msg,
	}
	global request_limit
	request_limit = 3
	response = client.post('/execute-tool/', json={'inputs': {'x': 4}})
	assert response.status_code == 200
	assert_output_values(response, expected_output)
