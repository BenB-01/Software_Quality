from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from rest_rce.src.constants import (
	INVALID_JSON_PATH,
	INVALID_KEY_JSON_PATH,
	TOOL_DIR,
	VALID_JSON_PATH,
)
from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.main import set_up_logger


# Pytest fixtures
@pytest.fixture
def mock_logger():
	return Mock()


@pytest.fixture
def main_logger():
	return set_up_logger()


@pytest.fixture
def root_json_handler():
	yield JsonHandler(main_logger, VALID_JSON_PATH)


# Pytest fixtures
@pytest.fixture
def json_essential_fields():
	essential_fields = {
		'enableCommandScriptWindows': True,
		'enableCommandScriptLinux': True,
		'commandScriptWindows': 'xyz',
		'setToolDirAsWorkingDir': False,
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
	assert isinstance(test_all_keys, list)


# Test 'validate_schema'
# Can throw errors because of incomplete list of possible keys
def test_validate_schema(root_json_handler):
	"""Tests 'validate_schema' method of class JSONHandler\n
	Notes:\n
	- Currently incomplete list of possible keys\n
	- Therefore, unknown keys of valid JSON-Files may raise INVALID KEY Errors
	"""
	try:
		root_json_handler.validate_schema()
	except ValueError:
		pytest.fail("'validate_schema' raised an unexpected value error")


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
def test_validate_essential_fields_launch_settings_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler,
	if launch settings are missing.\n Tests the following cases:\n
	- 'launchSettings' key is missing \n
	- 'launchSettings' is set to ''\n
	- 'launchSettings' is set to []\n
	"""
	pass


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
	pass
