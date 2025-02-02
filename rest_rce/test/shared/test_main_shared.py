from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from rest_rce.src.main import app, execution_status, tool_config
from rest_rce.src.utils import run_parse_arguments

client = TestClient(app)
request_limit = 10


@pytest.fixture
def mock_get_running_processes():
	"""Fixture to mock get_running_processes function."""
	with patch('rest_rce.src.main.get_running_processes') as mock_func:
		yield mock_func


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
		}
	)
	return tool_config


@pytest.fixture
def mock_execution_status():
	execution_status.update(
		{
			'task1': {'status': 'running', 'started_at': '2021-09-01T12:00:00'},
			'task2': {'status': 'completed', 'started_at': '2021-09-01T12:01:00'},
			'task3': {'status': 'running', 'started_at': '2021-09-01T12:02:00'},
		}
	)
	return execution_status


# Tests for parse_arguments

# Test following cases:
# - Required argument only
# - Required argument and timeout
# - Required argument and request limit
# - Required argument, timeout, and request limit
# - Missing required argument


def test_required_argument_only(monkeypatch):
	"""Test with only the required config file path."""
	args = ['script.py', 'config.json']
	config_file_path, timeout, limit = run_parse_arguments(args, monkeypatch)
	assert config_file_path == 'config.json'
	assert timeout is None
	assert limit is None


def test_with_timeout(monkeypatch):
	"""Test with required argument and timeout (-t)."""
	args = ['script.py', 'config.json', '-t', '30']
	config_file_path, timeout, limit = run_parse_arguments(args, monkeypatch)
	assert config_file_path == 'config.json'
	assert timeout == 30.0
	assert limit is None


def test_with_request_limit(monkeypatch):
	"""Test with required argument and request limit (-r)."""
	args = ['script.py', 'config.json', '-r', '100']
	config_file_path, timeout, limit = run_parse_arguments(args, monkeypatch)
	assert config_file_path == 'config.json'
	assert timeout is None
	assert limit == 100


def test_with_all_arguments(monkeypatch):
	"""Test with required argument, timeout (-t), and request limit (-r)."""
	args = ['script.py', 'config.json', '-t', '15', '-r', '50']
	config_file_path, timeout, limit = run_parse_arguments(args, monkeypatch)
	assert config_file_path == 'config.json'
	assert timeout == 15.0
	assert limit == 50


def test_missing_required_argument(monkeypatch):
	"""Test with no arguments, should raise a SystemExit."""
	args = ['script.py']  # No config file path
	with pytest.raises(SystemExit):
		run_parse_arguments(args, monkeypatch)


# Tests for the main FastAPI application

# Test following cases:
# - GET request to root endpoint
# - GET request to running-processes endpoint
# - POST request to execute-tool endpoint with request limit exceeded


def test_read_root(mock_tool_config):
	"""Test the basic get method."""
	response = client.get('/')
	assert response.status_code == 200
	assert response.json()['message'] == 'API is running. Tool configuration loaded.'


def test_get_running_processes(mock_execution_status):
	"""Test if the running processes are returned correctly."""
	expected_response = [
		['task1', {'status': 'running', 'started_at': '2021-09-01T12:00:00'}],
		['task3', {'status': 'running', 'started_at': '2021-09-01T12:02:00'}],
	]
	response = client.get('/running-processes/')
	assert response.status_code == 200
	assert response.json() == expected_response


def test_execute_tool_exceeds_limit(mock_get_running_processes):
	"""Test if execute_tool denies requests when request limit is reached."""
	mock_get_running_processes.return_value = [
		'task1',
		'task2',
		'task3',
		'task4',
		'task5',
		'task6',
		'task7',
		'task8',
		'task9',
		'task10',
	]
	global request_limit
	request_limit = 3
	response = client.post('/execute-tool/', json={'inputs': {'x': 4}})
	assert response.status_code == 429
	assert response.json()['detail'] == 'Request limit reached.'
