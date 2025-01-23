import json
import logging
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from rest_rce.src.json_handler import JsonHandler

VALID_JSON_PATH = 'rest_rce\\test\\root\\configuration.json'
INVALID_JSON_PATH = 'rest_rce\\test\\root\\syntax_invalid_configuration.json'
INVALID_KEY_JSON_PATH = 'rest_rce\\test\\root\\invalid_key_configuration.json'


# Pytest fixtures
@pytest.fixture
def mock_logger():
	return Mock()


@pytest.fixture
def main_logger():
	# Set up logging
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
	)

	log_file_handler = logging.FileHandler('tool_execution.log')
	log_file_handler.setFormatter(formatter)
	logger.addHandler(log_file_handler)

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)


@pytest.fixture
def root_json_handler():
	yield JsonHandler(main_logger, VALID_JSON_PATH)


@pytest.fixture()
def json_essential_fields():
	essential_fields = {
		'enableCommandScriptWindows': True,
		'enableCommandScriptLinux': True,
		'commandScriptWindows': 'xyz',
		'commandScriptLinux': 'xyz',
		'setToolDirAsWorkingDir': False,
		'launchSettings': [
			{
				'toolDirectory': 'xyz',
			}
		],
		'inputs': [{'endpointName': 'xName'}],
	}
	return essential_fields


# Test pyTest fixtures
def test_json_fixture(root_json_handler):
	"""Tests pytest.fixture that yields JSONHandler object"""
	test_json_handler = root_json_handler
	assert test_json_handler.__class__ == JsonHandler


# Test 'fetch_config_file_keys' method
def test_fetch_config_file_keys(root_json_handler):
	"""Tests 'fetch_config_file_keys' method of class JSONHandler"""
	test_all_keys = root_json_handler.fetch_config_file_keys()
	assert isinstance(test_all_keys, list)


# Test 'validate_schema'
# Can throw errors because of incomplete list of possible keys
def test_validate_schema(root_json_handler):
	"""Tests 'validate_schema' method of class JSONHandler\n
	Notes:\n
	- Currently uncomplete list of possible keys\n
	- Therefore, unknown keys of valid JSON-Files may raise INVALID KEY Errors
	"""
	with open(root_json_handler.file_path) as file:
		json_data = json.load(file)
	try:
		root_json_handler.validate_schema(json_data)
	except ValueError:
		pytest.fail("'validate_schema' raised an unexpected value error")


def test_validate_schema_invalid_key_error(root_json_handler):
	"""Tests error handling of 'validate_schema' method of class JSONHandler,
	if CLEARLY invalid keys are detected"""
	root_json_handler.file_path = INVALID_KEY_JSON_PATH
	with open(root_json_handler.file_path) as file:
		json_data = json.load(file)
	with pytest.raises(ValueError, match='The configuration file contains invalid keys:'):
		root_json_handler.validate_schema(json_data)


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


# Test 'extract_values' method
# For Linux: Still needs to be tested
# @patch("os.name", return_value='nt')
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_extract_values_command_script_disabled_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""
	Tests 'extract_values' method of class JSONHandler on Windows operating system,
	if the command script is not enabled.\n
	Tests the following cases:\n
	- 'enableCommandScriptWindows' is set to False\n
	- 'enableCommandScriptWindows' key is not in json file
	"""
	root_json_handler.validate_file()
	with pytest.raises(
		HTTPException, match='Command script execution is disabled in configuration file.'
	):
		json_essential_fields.__setitem__('enableCommandScriptWindows', False)
		root_json_handler.extract_values(json_essential_fields)
	with pytest.raises(
		HTTPException, match='Command script execution is disabled in configuration file.'
	):
		del json_essential_fields['enableCommandScriptWindows']
		root_json_handler.extract_values(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_extract_values_command_script_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'extract_values' method of class JSONHandler on Windows operating system,
	if the command script is missing.\n Tests the following cases:\n
	- 'commandScriptWindows' is set to False\n
	- 'enableCommandScriptWindows' key is not in json file
	"""
	root_json_handler.validate_file()
	with pytest.raises(
		HTTPException, match='No command script specified in the configuration file.'
	):
		json_essential_fields.__setitem__('commandScriptWindows', '')
		root_json_handler.extract_values(json_essential_fields)
	with pytest.raises(
		HTTPException, match='No command script specified in the configuration file.'
	):
		del json_essential_fields['commandScriptWindows']
		root_json_handler.extract_values(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_extract_values_set_tool_dir(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'extract_values' method of class JSONHandler,
	possible settings of 'setToolDirAsWorkingDir'.\n Tests the following cases:\n
	- 'setToolDirAsWorkingDir' is set to True\n
	- 'setToolDirAsWorkingDir' is set to False\n
	- 'setToolDirAsWorkingDir' key is not in json file --> will be set to False
	"""
	root_json_handler.validate_file()
	json_essential_fields.__setitem__('setToolDirAsWorkingDir', True)
	assert root_json_handler.extract_values(json_essential_fields)[1]
	json_essential_fields.__setitem__('setToolDirAsWorkingDir', False)
	assert not root_json_handler.extract_values(json_essential_fields)[1]
	del json_essential_fields['setToolDirAsWorkingDir']
	assert not root_json_handler.extract_values(json_essential_fields)[1]


# 'extract_values' throws not-yet-handled error if 'launchSettings' key is missing
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_extract_values_tool_dir_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'extract_values' method of class JSONHandler,
	if tool directory is missing.\n Tests the following cases:\n
	- 'toolDirectory' key is missing (Not in 'launchSettings', 'launchSettings' empty)\n
	- 'toolDirectory' key is missing (Not in 'launchSettings', 'launchSettings' not empty)\n
	- 'toolDirectory' key is missing ('launchSettings' key is missing)\n
	- 'toolDirectory' is set to ''\n
	"""
	root_json_handler.validate_file()
	with pytest.raises(
		HTTPException, match='No tool directory specified in the configuration file.'
	):
		json_essential_fields.get('launchSettings')[0].__setitem__('toolDirectory', '')
		root_json_handler.extract_values(json_essential_fields)
	with pytest.raises(
		HTTPException, match='No tool directory specified in the configuration file.'
	):
		del json_essential_fields.get('launchSettings')[0]['toolDirectory']
		root_json_handler.extract_values(json_essential_fields)
	with pytest.raises(
		HTTPException, match='No tool directory specified in the configuration file.'
	):
		json_essential_fields.get('launchSettings')[0]['otherKey'] = 'randomString'
		root_json_handler.extract_values(json_essential_fields)
	with pytest.raises(
		HTTPException, match='No tool directory specified in the configuration file.'
	):
		del json_essential_fields['launchSettings']
		root_json_handler.extract_values(json_essential_fields)
