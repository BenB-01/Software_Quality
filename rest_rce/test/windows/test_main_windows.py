import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from rest_rce.src.main import app, tool_config
from rest_rce.test.shared.test_main_shared import assert_output_values

client = TestClient(app)


@pytest.fixture
def mock_tool_config():
	tool_config.update(
		{
			'enableCommandScriptWindows': True,
			'commandScriptWindows': 'root.exe ${in:x}',
			'setToolDirAsWorkingDir': True,
			'launchSettings': [{'toolDirectory': 'C:\\Tools\\Root'}],
			'inputs': [{'endpointName': 'x', 'endpointDataType': 'Float'}],
			'outputs': [{'endpointName': 'root', 'endpointDataType': 'Float'}],
			'postScript': 'file = open("${dir:tool}/result.txt","r")'
			'\r\nroot = file.read()'
			'\r\n${out:root} = float(root)',
			'preScript': 'import time'
			'\r\nimport random'
			'\r\ndelay=random.uniform(1,3)'
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
