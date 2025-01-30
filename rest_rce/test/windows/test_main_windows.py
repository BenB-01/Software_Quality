import asyncio

import pytest
from fastapi.testclient import TestClient

from rest_rce.src.main import app, tool_config

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


def test_read_root(mock_tool_config):
	response = client.get('/')
	assert response.status_code == 200
	assert response.json()['message'] == 'API is running. Tool configuration loaded.'


def assert_output_values(res, expected_out):
	"""Validate the response from the tool execution."""
	assert res.status_code == 200, f'Unexpected status {res.status_code}: {res.json()}'

	res_json = res.json()

	assert 'stdout' in res_json, f'Missing stdout in response: {res_json}'
	assert 'command' in res_json, f'Missing command in response: {res_json}'
	assert 'output_variables' in res_json, f'Missing output_variables in response: {res_json}'

	# Compare command and output values
	expected_c, response_c = expected_out['command'], res_json['command']
	assert response_c == expected_c, f'Command mismatch: expected {expected_c}, got {response_c}'
	expected_ov, response_ov = expected_out['output_variables'], res_json['output_variables']
	assert response_ov == expected_ov, f'Output mismatch: expected {expected_ov}, got {response_ov}'


def test_execute_tool(mock_tool_config):
	"""Test execution of the tool with a single input."""
	test_input = {'inputs': {'x': 4}}
	expected_output = {'command': 'root.exe 4', 'output_variables': {'root': 2.0}}

	# Send a synchronous POST request
	response = client.post('/execute-tool/', json=test_input)

	# Verify response
	assert_output_values(response, expected_output)


@pytest.mark.asyncio
async def test_parallel_tool_execution(mock_tool_config):
	"""Test parallel execution of the tool with different inputs."""

	test_inputs = [
		{'inputs': {'x': 4}},
		{'inputs': {'x': 16}},
		{'inputs': {'x': 64}},
	]

	expected_outputs = [
		{'command': 'root.exe 4', 'output_variables': {'root': 2.0}},
		{'command': 'root.exe 16', 'output_variables': {'root': 4.0}},
		{'command': 'root.exe 64', 'output_variables': {'root': 8.0}},
	]

	async def send_request(data):
		response = client.post('/execute-tool/', json=data)
		return response

	# Run all requests parallel
	responses = await asyncio.gather(*[send_request(data) for data in test_inputs])

	# Verify responses
	for response, expected_output in zip(responses, expected_outputs):
		assert_output_values(response, expected_output)
