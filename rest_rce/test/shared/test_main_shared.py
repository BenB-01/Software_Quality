from fastapi.testclient import TestClient

from rest_rce.src.main import app

client = TestClient(app)


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
	expected_stdout, response_stdout = expected_out['stdout'], res_json['stdout']
	assert (
		response_stdout == expected_stdout
	), f'Command mismatch: expected {expected_stdout}, got {response_stdout}'
	expected_c, response_c = expected_out['command'], res_json['command']
	assert response_c == expected_c, f'Command mismatch: expected {expected_c}, got {response_c}'
	expected_ov, response_ov = expected_out['output_variables'], res_json['output_variables']
	assert response_ov == expected_ov, f'Output mismatch: expected {expected_ov}, got {response_ov}'
