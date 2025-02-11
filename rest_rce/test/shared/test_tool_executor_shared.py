import json
import os
import re
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from rest_rce.src.constants import VALID_JSON_PATH
from rest_rce.src.main import request_id_var
from rest_rce.src.tool_executor import ToolExecutor
from rest_rce.src.utils import set_up_logger


# Pytest fixtures
@pytest.fixture
def main_logger():
	return set_up_logger(request_id_var)


@pytest.fixture
def mock_logger():
	return MagicMock()


@pytest.fixture
def mock_tool_executor(main_logger):
	with open(VALID_JSON_PATH) as file:
		configuration = json.load(file)
	yield ToolExecutor(tool_config=configuration, inputs={'x': 4}, logger=main_logger)


@pytest.fixture
def mock_project_dir(tmp_path):
	project_dir = tmp_path / 'my_project'
	project_dir.mkdir()
	(project_dir / 'pyproject.toml').write_text("[tool.poetry]\nname = 'example'")

	sub_dir = project_dir / 'src'
	sub_dir.mkdir()
	return sub_dir


@pytest.fixture
def mock_clean_input_int():
	clean_input = [
		{
			'inputHandling': 'Constant',
			'endpointFileName': '',
			'endpointDataType': 'Integer',
			'defaultInputExecutionConstraint': 'NotRequired',
			'endpointName': 'x',
			'defaultInputHandling': 'Constant',
			'inputExecutionConstraint': 'NotRequired',
			'endpointFolder': '',
		}
	]
	return clean_input


@pytest.fixture
def mock_input_int_without_endpointdatatype():
	broken_input = [
		{
			'inputHandling': 'Constant',
			'endpointFileName': '',
			'defaultInputExecutionConstraint': 'NotRequired',
			'endpointName': 'x',
			'defaultInputHandling': 'Constant',
			'inputExecutionConstraint': 'NotRequired',
			'endpointFolder': '',
		}
	]
	return broken_input


@pytest.fixture
def mock_input_int_without_endpointname():
	broken_input = [
		{
			'inputHandling': 'Constant',
			'endpointFileName': '',
			'endpointDataType': 'Integer',
			'defaultInputExecutionConstraint': 'NotRequired',
			'defaultInputHandling': 'Constant',
			'inputExecutionConstraint': 'NotRequired',
			'endpointFolder': '',
		}
	]
	return broken_input


# Test 'validate_inputs' method

# The following error cases are tested:
# - No inputs/empty list in 'self.tool_config' and 'self.inputs'
# - Broken input in 'self.tool_config' (no endpointName/endpointDataType)
# - Input Missing: Not in 'self.inputs' but 'self.tool_config'
# - Unexpected input provided
# - Empty input value given via 'self.inputs'
# - Wrong input data type: 'validate_input_datatypes' throws ValueError


def test_validate_inputs_no_inputs(mock_tool_executor):
	"""Tests 'validate_inputs' method, if no inputs are required nor provided"""
	mock_tool_executor.inputs = {}
	mock_tool_executor.tool_config['inputs'] = []
	mock_tool_executor.validate_inputs()


def test_validate_inputs_broken_config(
	mock_tool_executor, mock_input_int_without_endpointname, mock_input_int_without_endpointdatatype
):
	"""
	Tests 'validate_inputs' method, if the 'tool.config' contains a broken input.\n
	I.e. 'endpointName' or 'endpointDataType' are missing.
	"""
	# Tests if endpointName is missing
	mock_tool_executor.inputs = {'x': 1}
	mock_tool_executor.tool_config['inputs'] = mock_input_int_without_endpointname
	with pytest.raises(KeyError):
		mock_tool_executor.validate_inputs()
	# Tests if endpointDataType is missing
	mock_tool_executor.tool_config['inputs'] = mock_input_int_without_endpointdatatype
	with pytest.raises(AttributeError):
		mock_tool_executor.validate_inputs()


def test_validate_inputs_missing_input(mock_tool_executor, mock_clean_input_int):
	"""Tests 'validate_inputs' method, if an input is required but not provided"""
	mock_tool_executor.inputs = {}
	mock_tool_executor.tool_config['inputs'] = mock_clean_input_int
	with pytest.raises(ValueError, match='Post request missing required input'):
		mock_tool_executor.validate_inputs()


def test_validate_inputs_unexpected_input(mock_tool_executor, mock_clean_input_int):
	"""Tests 'validate_inputs' method, if an unexpected input is provided"""
	mock_tool_executor.inputs = {'unexpectedInput1': 187, 'unexpectedInput2': 'this'}
	mock_tool_executor.tool_config['inputs'] = mock_clean_input_int
	with pytest.raises(ValueError, match='Post request containing unexpected inputs:'):
		mock_tool_executor.validate_inputs()


def test_validate_inputs_missing_value(mock_tool_executor, mock_clean_input_int):
	"""Tests 'validate_inputs' method, if an input key is provided but not an input value"""
	mock_tool_executor.inputs = {'x': None}
	mock_tool_executor.tool_config['inputs'] = mock_clean_input_int
	with pytest.raises(ValueError, match='Input value for'):
		mock_tool_executor.validate_inputs()


def test_validate_inputs_datatype_error(mock_tool_executor, mock_clean_input_int):
	"""Tests 'validate_inputs' method, if an input value has an unexpected data type"""
	mock_tool_executor.inputs = {'x': 'this is not an integer value'}
	mock_tool_executor.tool_config['inputs'] = mock_clean_input_int
	with pytest.raises(ValueError):
		mock_tool_executor.validate_inputs()


# Test 'validate_outputs' method

# The following error cases are tested:
# - The tool returns an unexpected output variable
# - An expected output is set to None
# - An expected output has the correct data type like specified in the configuration
# - An expected output has a different data type than specified in the configuration


def test_validate_outputs_unexpected_output(mock_tool_executor):
	"""Tests 'validate_outputs' when the tool returns an unexpected output variable."""
	mock_tool_executor.tool_config['outputs'] = [{'endpointName': 'expected_output'}]
	output_vars = {'unexpected_output': 'some_value'}
	msg = "Tool returned outputs not defined in the config file: ['unexpected_output']"
	with pytest.raises(ValueError, match=re.escape(msg)):
		mock_tool_executor.validate_outputs(output_vars)


def test_validate_outputs_missing_value(mock_tool_executor):
	"""Tests 'validate_outputs' when an expected output is set to None."""
	mock_tool_executor.tool_config['outputs'] = [{'endpointName': 'valid_output'}]
	output_vars = {'valid_output': None}
	with pytest.raises(ValueError, match='Output value for valid_output is empty.'):
		mock_tool_executor.validate_outputs(output_vars)


def test_validate_outputs_valid(mock_tool_executor):
	"""Tests 'validate_outputs' with a valid output that matches the configuration."""
	mock_tool_executor.tool_config['outputs'] = [
		{'endpointName': 'valid_output', 'endpointDataType': 'String'}
	]
	output_vars = {'valid_output': 'test_string'}
	# Should not raise an exception
	mock_tool_executor.validate_outputs(output_vars)


def test_validate_outputs_invalid_data_type(mock_tool_executor):
	"""Tests 'validate_outputs' when output data type doesn't match the expected type."""
	mock_tool_executor.tool_config['outputs'] = [
		{'endpointName': 'x', 'endpointDataType': 'Integer'}
	]
	output_vars = {'x': 'not_an_integer'}
	with pytest.raises(ValueError, match='Expected Integer, but got str: not_an_integer'):
		mock_tool_executor.validate_outputs(output_vars)


# Test 'execute_python_script' method

# The following cases are tested:
# - Running a simple Python script
# - Running a Python script with a placeholder for the output variable
# - Running a Python script with an import error
# - Running a Python script with an import error that fails to import the module
# - Running a Python script that raises an error itself


def test_execute_python_script(mock_tool_executor, mock_project_dir):
	"""Tests if 'execute_python_script' method can execute simple Python script."""
	mock_tool_dir = 'rest_rce/test/tools/root'
	script = "print('This is a pre script.')"
	mock_tool_executor.execute_python_script(
		script=script, project_dir=mock_project_dir, tool_dir=mock_tool_dir
	)


def test_execute_python_script_replace_output_placeholder(mock_tool_executor):
	"""Tests if the output variable placeholder is replaced with the correct value"""
	tool_dir = 'rest_rce/test/tools/root'
	project_dir = mock_tool_executor.find_project_directory(os.getcwd())
	script = (
		'file = open("${dir:tool}/result.txt","r")\r\nroot = file.read()\r\n'
		+ '${out:root} = float(root)'
	)
	output_vars = {'k': 1}
	returned_value = mock_tool_executor.execute_python_script(
		script=script, project_dir=project_dir, tool_dir=tool_dir, output_vars=output_vars
	)

	assert returned_value != {}


def test_execute_python_script_import_error(mock_tool_executor):
	"""Tests 'execute_python_script' method when an import error occurs."""
	tool_dir = 'rest_rce/test/tools/root'
	project_dir = mock_tool_executor.find_project_directory(os.getcwd())
	script = (
		'import emoji\r\n'
		+ 'file = open("${dir:tool}/result.txt","r")\r\nroot = file.read()\r\n'
		+ '${out:root} = float(root)'
	)
	mock_tool_executor.logger = MagicMock()
	output_vars = {'k': 1}
	mock_tool_executor.execute_python_script(
		script=script, project_dir=project_dir, tool_dir=tool_dir, output_vars=output_vars
	)
	warning_msg = 'Missing dependency detected: emoji. Attempting to install it.'
	mock_tool_executor.logger.warning.assert_called_with(warning_msg)


def test_execute_python_script_import_error_failed_import(mock_tool_executor):
	"""Tests if the correct error is raised if missing libraries could not be installed."""
	tool_dir = 'rest_rce/test/tools/root'
	project_dir = mock_tool_executor.find_project_directory(os.getcwd())
	script = (
		'import ThisIsNotARealModule\r\n'
		+ 'file = open("${dir:tool}/result.txt","r")\r\nroot = file.read()\r\n'
		+ '${out:root} = float(root)'
	)
	output_vars = {'k': 1}
	with pytest.raises(subprocess.CalledProcessError):
		mock_tool_executor.execute_python_script(
			script=script, project_dir=project_dir, tool_dir=tool_dir, output_vars=output_vars
		)


@patch('os.chdir')
@patch('subprocess.run')
def test_execute_script_with_exception(mock_subprocess, mock_chdir, mock_tool_executor):
	"""Test if the right exception is raised inside a Python script."""
	script = "raise ValueError('Test error')"
	tool_dir = '/fake/tool'
	project_dir = '/fake/project'
	output_vars = {}

	with pytest.raises(ValueError, match='Test error'):
		mock_tool_executor.execute_python_script(script, tool_dir, project_dir, output_vars)

	# mock_chdir.assert_called_with(project_dir)
	mock_subprocess.assert_not_called()


@pytest.mark.parametrize(
	'p_dt_value, p_not_dt_value, p_config_datatype, p_error_string',
	[
		('thisIsAString', 1, 'string', 'Expected String, but got'),
		(1, 'this is not an integer', 'integer', 'Expected Integer, but got'),
		(1.1, 1, 'float', 'Expected Float, but got'),  # No ValueError if float expected & int given
		(1.1, 'this is not a float', 'float', 'Expected Float, but got'),
		(True, 12, 'boolean', 'Expected Boolean, but got'),
		([1, 2, 3], 123, 'list', 'Expected Array/List, but got'),
		('FileReferenceString.xml', 1.1, 'filereference', 'Expected path string, but got'),
		({'Dict': 'ionary'}, 'this is not a dict', 'map', 'Expected Map'),
		(1123, 132, 'not a data type', 'Unsupported endpoint data type'),
	],
	ids=[
		'str_expected',
		'int_expected',
		'float_expected_int_given',
		'float_expected_str_given',
		'bool_expected',
		'list_expected',
		'filereference_expected',
		'dict_expected',
		'unsupported_endpoint',
	],
)
def test_validate_input_datatypes_string_value(
	p_dt_value, p_not_dt_value, p_config_datatype, p_error_string, mock_tool_executor
):
	if p_config_datatype != 'not a data type':
		mock_tool_executor.validate_input_datatypes(p_dt_value, p_config_datatype)
	# Catch case: "float_expected_int_given"
	if isinstance(p_not_dt_value, int) & (p_config_datatype == 'float'):
		return True
	with pytest.raises(ValueError, match=p_error_string):
		mock_tool_executor.validate_input_datatypes(p_not_dt_value, p_config_datatype)


def test_find_project_directory(mock_tool_executor, mock_project_dir):
	"""Tests 'find_project_directory' method of class ToolExecutor"""
	# Test if .pyproject.toml exists
	project_dir = mock_tool_executor.find_project_directory(mock_project_dir)
	assert project_dir is not None
	assert os.path.basename(project_dir) == 'my_project'
	# Test if .pyproject.toml does not exist
	with patch('os.path.exists', return_value=False):
		project_dir = mock_tool_executor.find_project_directory(mock_project_dir)
		assert project_dir is None
