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
			'enableCommandScriptLinux': True,
			'commandScriptLinux': './poly.sh ${in:x} ${in:n}',
			'setToolDirAsWorkingDir': True,
			'launchSettings': [{'toolDirectory': 'rest_rce/test/tools/poly/'}],
			'inputs': [
				{'endpointName': 'x', 'endpointDataType': 'Float'},
				{'endpointName': 'n', 'endpointDataType': 'Float'},
			],
			'outputs': [{'endpointName': 'fx', 'endpointDataType': 'FileReference'}],
			'postScript': '${out:fx} = "${dir:tool}/result"',
			'preScript': 'import time'
			'\r\nimport random'
			'\r\ndelay=random.uniform(1,3)'
			'\r\ntime.sleep(delay)',
		}
	)
	return tool_config


def test_execute_tool_linux(mock_tool_config):
	"""Test execution of the tool in Ubuntu with a single input."""
	test_input = {'inputs': {'x': 2, 'n': 4}}
	output_file_path = 'rest_rce/test/tools/poly//result'
	stdout = 'Calculating exp\nReceived parameter x=2\nReceived parameter n=4\nResult: 16\n'
	expected_output = {
		'command': './poly.sh 2 4',
		'output_variables': {'fx': output_file_path},
		'stdout': stdout,
	}

	# Send a synchronous POST request
	response = client.post('/execute-tool/', json=test_input)

	# Verify response
	assert_output_values(response, expected_output)


@pytest.mark.asyncio
async def test_parallel_tool_execution_linux(mock_tool_config):
	"""Test parallel execution of the tool in Ubuntu with different inputs."""

	# Define test inputs and expected outputs
	inputs = [[2, 2], [2, 3], [2, 4]]
	test_inputs = []
	expected_outputs = []
	stdout_template = (
		'Calculating exp\nReceived parameter x={x}\nReceived parameter n={n}\nResult: {res}\n'
	)

	for lst in inputs:
		x, n = lst[0], lst[1]
		res = int(x**n)
		stdout_success_msg = stdout_template.format(x=x, n=n, res=res)
		test_inputs.append({'inputs': {'x': x, 'n': n}})
		expected_outputs.append(
			{
				'command': f'./poly.sh {x} {n}',
				'output_variables': {'fx': 'rest_rce/test/tools/poly//result'},
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
