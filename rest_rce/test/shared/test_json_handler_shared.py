from unittest.mock import Mock, patch

import pytest
import requests
from fastapi import HTTPException

from rest_rce.src.constants import (
	CS_L,
	CS_W,
	ENABLE_CS_L,
	ENABLE_CS_W,
	INPUTS,
	INVALID_JSON_PATH,
	INVALID_KEY_JSON_PATH,
	LAUNCH_SETTINGS,
	OUTPUTS,
	TOOL_DIR,
	VALID_JSON_PATH,
)
from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.main import request_id_var
from rest_rce.src.utils import set_up_logger


# Pytest fixtures
@pytest.fixture
def mock_logger():
	return Mock()


@pytest.fixture
def main_logger():
	return set_up_logger(request_id_var)


@pytest.fixture
def root_json_handler(main_logger):
	yield JsonHandler(main_logger, VALID_JSON_PATH)


# Pytest fixtures
@pytest.fixture
def json_essential_fields(
	p_enable_csw=True,
	p_enable_csl=True,
	p_csw='this is a windows command script',
	p_csl='this is a linux command script',
	p_set_tooldir_as_workdir=False,
):
	essential_fields = {
		'enableCommandScriptWindows': p_enable_csw,
		'enableCommandScriptLinux': p_enable_csl,
		'commandScriptWindows': p_csw,
		'commandScriptLinux': p_csl,
		'setToolDirAsWorkingDir': p_set_tooldir_as_workdir,
		'launchSettings': [{'toolDirectory': 'xyz'}],
		'inputs': [{'endpointName': 'xName'}],
		'outputs': [{'endpointName': 'xName'}],
	}
	return essential_fields


# Tests that can be done in both operating systems
# Test pyTest fixtures
def test_json_fixture(root_json_handler):
	"""Tests pytest.fixture that yields JSONHandler object"""
	test_json_handler = root_json_handler
	assert test_json_handler.__class__ == JsonHandler


# Test 'fetch_config_file_keys' method
def test_fetch_config_file_keys(root_json_handler):
	"""Tests 'fetch_config_file_keys' method of class JSONHandler"""
	test_all_keys = root_json_handler.fetch_config_file_keys()
	assert test_all_keys != []


def test_fetch_config_file_keys_http_error(root_json_handler):
	"""Tests 'fetch_config_file_keys' method of class JSONHandler, if
	- 'requests.get' raises an exception, possible exceptions are:
		- 'ConnectionError'
		- 'Timeout' (if a timeout is defined)
		- 'TooManyRedirects'
	- 'requests.Response.raise_for_status' returns HTTPError
	"""
	# with patch('requests.get', side_effect=requests.RequestException):
	# 	returned_keys = root_json_handler.fetch_config_file_keys()
	# 	assert returned_keys == []
	with patch('requests.Response.raise_for_status', side_effect=requests.HTTPError):
		returned_keys = root_json_handler.fetch_config_file_keys()
		assert returned_keys == []


# Test 'validate_schema'
# Can throw errors because of incomplete list of possible keys
# def test_validate_schema(root_json_handler):
# 	"""Tests 'validate_schema' method of class JSONHandler\n
# 	Notes:\n
# 	- Currently incomplete list of possible keys\n
# 	- Therefore, unknown keys of valid JSON-Files may raise INVALID KEY Errors
# 	"""
# 	try:
# 		root_json_handler.validate_schema()
# 	except ValueError:
# 		pytest.fail("'validate_schema' raised an unexpected value error")


def test_validate_schema_invalid_key_error(root_json_handler):
	"""Tests error handling of 'validate_schema' method of class JSONHandler,
	if CLEARLY invalid keys are detected"""
	root_json_handler.file_path = INVALID_KEY_JSON_PATH
	with pytest.raises(ValueError, match='The configuration file contains invalid keys:'):
		root_json_handler.validate_schema()


# Test 'validate_file' method
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_file_result(mock_validate_schema, root_json_handler):
	"""Tests result of 'validate_file' method of class JSONHandler"""
	result_json = root_json_handler.validate_file()
	assert isinstance(result_json, dict)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_file_invalid_filetype_error(mock_validate_schema, root_json_handler):
	"""Tests 'validate_file' method of class JSONHandler,
	if invalid file type is given as input (not .json)"""
	with pytest.raises(ValueError, match='Invalid file type:'):
		root_json_handler.file_path = 'not_endswith_json.py'
		root_json_handler.validate_file()


@patch('os.path.exists', return_value=False)
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_file_file_not_found_error(
	mock_validate_schema, mock_path_exists, root_json_handler
):
	"""Tests 'validate_file' method of class JSONHandler, if file path does not lead to a file"""
	with pytest.raises(FileNotFoundError):
		root_json_handler.validate_file()


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_file_invalid_jsonsyntax_error(mock_validate_schema, root_json_handler):
	"""Tests 'validate_file' method of class JSONHandler, if JSON has invalid syntax.
	JSON syntax error tested:\n
	- Trailing comma after last value
	"""
	with pytest.raises(ValueError, match='Invalid JSON syntax in file'):
		root_json_handler.file_path = INVALID_JSON_PATH
		root_json_handler.validate_file()


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_essential_fields_tool_dir_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler,
	if tool directory is missing.\n Tests the following cases:\n
	- 'toolDirectory' is set to ''\n
	- 'toolDirectory' key is missing \n
	"""
	root_json_handler.validate_file()
	message = (
		f'Tool directory not specified in the configuration file. '
		f"Specify directory with key '{TOOL_DIR}' in launch settings."
	)
	with pytest.raises(HTTPException, match=message):
		json_essential_fields.get('launchSettings')[0].__setitem__('toolDirectory', '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message):
		del json_essential_fields.get('launchSettings')[0]['toolDirectory']
		root_json_handler.validate_essential_fields(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_essential_fields_inputs_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler,
	if inputs are missing.\n Tests the following cases:\n
	- 'inputs' key is missing \n
	- 'inputs' is set to ''\n
	- 'inputs' is set to []\n
	"""
	message = f'Inputs not specified in the configuration file. ' f'Please add the key "{INPUTS}".'
	# Test when 'inputs' key is missing
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		del test_json_data['inputs']
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'inputs' key is set to ''
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['inputs'] = ''
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'inputs' key is set to []
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['inputs'] = []
		root_json_handler.validate_essential_fields(test_json_data)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_essential_fields_launch_settings_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler,
	if launch settings are missing.\n Tests the following cases:\n
	- 'launchSettings' key is missing \n
	- 'launchSettings' is set to ''\n
	- 'launchSettings' is set to []\n
	"""
	message = (
		f'Launch settings not specified in the configuration file. '
		f'Please add the key "{LAUNCH_SETTINGS}".'
	)
	# Test when 'launchSettings' key is missing
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		del test_json_data['launchSettings']
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'launchSettings' key is set to ''
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['launchSettings'] = ''
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'launchSettings' key is set to []
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['launchSettings'] = []
		root_json_handler.validate_essential_fields(test_json_data)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_essential_fields_outputs_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler,
	possible settings of 'outputs'.\n Tests the following cases:\n
	- 'outputs' key is missing \n
	- 'outputs' is set to ''\n
	- 'outputs' is set to []\n
	"""
	message = (
		f'Outputs not specified in the configuration file. ' f'Please add the key "{OUTPUTS}".'
	)
	# Test when 'outputs' key is missing
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		del test_json_data['outputs']
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'outputs' key is set to ''
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['outputs'] = ''
		root_json_handler.validate_essential_fields(test_json_data)
	# Test when 'outputs' key is set to []
	with pytest.raises(HTTPException, match=message):
		test_json_data = json_essential_fields
		test_json_data['outputs'] = []
		root_json_handler.validate_essential_fields(test_json_data)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_validate_essential_fields_command_script_disabled_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""
	Tests 'validate_essential_fields' method of class JSONHandler on Windows & Linux operating
	system, if the command script is not enabled.\n
	Tests the following cases, if os is Windows:\n
	- 'enableCommandScriptWindows' is set to False\n
	- 'enableCommandScriptWindows' key is not in json file
	Tests the following cases, if os is Linux:\n
	- 'enableCommandScriptLinux' is set to False\n
	- 'enableCommandScriptLinux' key is not in json file
	"""
	root_json_handler.validate_file()
	message_w = (
		f'422: Command script execution is disabled in the configuration file. '
		f'Set field {ENABLE_CS_W} to True'
	)
	message_l = (
		f'422: Command script execution is disabled in the configuration file. '
		f'Set field {ENABLE_CS_L} to True'
	)
	with pytest.raises(HTTPException, match=message_w), patch('os.name', 'nt'):
		json_essential_fields.__setitem__(ENABLE_CS_W, False)
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message_w), patch('os.name', 'nt'):
		del json_essential_fields[ENABLE_CS_W]
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message_l), patch('os.name', 'posix'):
		json_essential_fields.__setitem__(ENABLE_CS_L, False)
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message_l), patch('os.name', 'posix'):
		del json_essential_fields[ENABLE_CS_L]
		root_json_handler.validate_essential_fields(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_validate_essential_fields_command_script_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler on Windows & Linux
	operating system, if the command script is missing.\n
	Tests the following cases, if os is Windows:\n
	- 'commandScriptWindows' is set to False\n
	- 'commandScriptWindows' key is not in json file
	Tests the following cases, if os is Linux:\n
	- 'commandScriptLinux' is set to False\n
	- 'commandScriptLinux' key is not in json file
	"""
	root_json_handler.validate_file()
	message_w = (
		f'Command script not specified in the configuration file. Please add the key "{CS_W}".'
	)
	message_l = (
		f'Command script not specified in the configuration file. Please add the key "{CS_L}".'
	)
	# Test for Windows
	with pytest.raises(HTTPException, match=message_w), patch('os.name', 'nt'):
		json_essential_fields.__setitem__(CS_W, '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message_w), patch('os.name', 'nt'):
		del json_essential_fields[CS_W]
		root_json_handler.validate_essential_fields(json_essential_fields)
	# Test for Linux
	with pytest.raises(HTTPException, match=message_l), patch('os.name', 'posix'):
		json_essential_fields.__setitem__(CS_L, '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message_l), patch('os.name', 'posix'):
		del json_essential_fields[CS_L]
		root_json_handler.validate_essential_fields(json_essential_fields)
