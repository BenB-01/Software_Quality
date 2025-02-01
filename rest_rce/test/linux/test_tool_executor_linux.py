import json
from unittest.mock import patch

import pytest

from rest_rce.src.constants import CS_L, ENABLE_CS_L, ENABLE_CS_W, POST_S, POLY_VAlID_JSON_PATH
from rest_rce.src.main import set_up_logger
from rest_rce.src.tool_executor import ToolExecutor


@pytest.fixture
def main_logger():
	return set_up_logger()


@pytest.fixture
def mock_tool_executor_timeout_linux(main_logger):
	with open(POLY_VAlID_JSON_PATH) as file:
		configuration = json.load(file)
	configuration[CS_L] = './poly_timeout.sh ${in:x} ${in:n}'
	configuration[ENABLE_CS_L] = True
	configuration[ENABLE_CS_W] = False
	configuration[POST_S] = ''
	yield ToolExecutor(
		tool_config=configuration, inputs={'x': 2, 'n': 4}, logger=main_logger, timeout=0.05
	)


# Test 'execute_tool' method for runs in Ubuntu operating system

# The following cases are tested:
# - Tool is executed without a timeout
# - Project directory is found when the tool is executed
# - Tool times out and raises a TimeoutExpired exception
# - Tool is executed without a timeout and the execution time is below the timeout value


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_no_timeout_linux(mock_script_execution, mock_tool_executor_timeout_linux):
	"""Test if the command script is correctly executed in Ubuntu if there is no timeout set."""
	mock_tool_executor_timeout_linux.timeout = None
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout_linux.execute_tool()
	)
	msg = 'Calculating exp\nReceived parameter x=2\nReceived parameter n=4\nResult: 16\n'
	assert return_code == 0
	assert stdout.rstrip('\n') == msg.rstrip('\n')


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_missing_project_dir_linux(
	mock_script_execution, mock_tool_executor_timeout_linux
):
	mock_tool_executor_timeout_linux.tool_config[CS_L] = './poly.sh ${in:x} ${in:n}'
	with (
		patch('rest_rce.src.tool_executor.ToolExecutor.find_project_directory', return_value=None),
		pytest.raises(FileNotFoundError),
	):
		mock_tool_executor_timeout_linux.execute_tool()


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_timeout_error_linux(mock_script_execution, mock_tool_executor_timeout_linux):
	"""Check if the command script is correctly terminated in Ubuntu if timeout is reached."""
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout_linux.execute_tool()
	)
	assert return_code == -1
	assert 'Timeout expired' in stderr


@patch('rest_rce.src.tool_executor.ToolExecutor.execute_python_script')
def test_execute_tool_timeout_not_reached_linux(
	mock_script_execution, mock_tool_executor_timeout_linux
):
	"""Test if command script is correctly executed in Ubuntu if timeout parameter
	is above execution time."""
	mock_tool_executor_timeout_linux.timeout = 3
	mock_tool_executor_timeout_linux.inputs = {'x': 2, 'n': 2}
	return_code, stdout, stderr, tool_directory, command_script, output_vars = (
		mock_tool_executor_timeout_linux.execute_tool()
	)
	msg = 'Calculating exp\nReceived parameter x=2\nReceived parameter n=2\nResult: 4\n'
	assert return_code == 0
	assert stdout == msg
