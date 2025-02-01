import json
from unittest.mock import patch

import pytest

from rest_rce.src.constants import CS_W, POST_S, POLY_VAlID_JSON_PATH
from rest_rce.src.main import set_up_logger
from rest_rce.src.tool_executor import ToolExecutor


@pytest.fixture
def main_logger():
	return set_up_logger()


@pytest.fixture
def mock_tool_executor_timeout(main_logger):
	with open(POLY_VAlID_JSON_PATH) as file:
		configuration = json.load(file)
	configuration[CS_W] = 'poly_timeout.bat ${in:x} ${in:n}'
	configuration[POST_S] = ''
	yield ToolExecutor(
		tool_config=configuration, inputs={'x': 2, 'n': 4}, logger=main_logger, timeout=0.05
	)


# Test 'execute_tool' method for runs in Windows operating system

# The following cases are tested:
# - Tool is executed without a timeout
# - Project directory is found when the tool is executed
# - Tool times out and raises a TimeoutExpired exception
# - Tool is executed without a timeout and the execution time is below the timeout value


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_no_timeout_windows(mock_script_execution, mock_tool_executor_timeout):
	"""Test if the command script is correctly executed in Windows if there is no timeout set."""
	mock_tool_executor_timeout.timeout = None
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout.execute_tool()
	)
	msg = 'Calculating exp\nReceived parameter x=2\nReceived parameter n=4\nResult: 16\n'
	assert return_code == 0
	assert stdout.rstrip('\n') == msg.rstrip('\n')


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_missing_project_dir_windows(
	mock_script_execution, mock_tool_executor_timeout
):
	with (
		patch('rest_rce.src.tool_executor.ToolExecutor.find_project_directory', return_value=None),
		pytest.raises(FileNotFoundError),
	):
		mock_tool_executor_timeout.execute_tool()


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_timeout_error_windows(mock_script_execution, mock_tool_executor_timeout):
	"""Check if the command script is correctly terminated in Windows if timeout is reached."""
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout.execute_tool()
	)
	assert return_code == -1
	assert 'Timeout expired' in stderr


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_timeout_not_reached_windows(
	mock_script_execution, mock_tool_executor_timeout
):
	"""Test if command script is correctly executed in Windows if the timeout
	value is above execution time."""
	mock_tool_executor_timeout.timeout = 3
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout.execute_tool()
	)
	msg = 'Calculating exp\nReceived parameter x=2\nReceived parameter n=4\nResult: 16\n'
	assert return_code == 0
	assert stdout == msg
