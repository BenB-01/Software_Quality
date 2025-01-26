from unittest.mock import patch

import pytest
from fastapi import HTTPException

from rest_rce.src.constants import CS_W, ENABLE_CS_W, TOOL_DIR, VALID_JSON_PATH
from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.main import set_up_logger


# Pytest fixtures
@pytest.fixture
def json_essential_fields():
	essential_fields = {
		'enableCommandScriptWindows': True,
		'commandScriptWindows': 'xyz',
		'setToolDirAsWorkingDir': False,
		'launchSettings': [{'toolDirectory': 'xyz'}],
		'inputs': [{'endpointName': 'xName'}],
		'outputs': [{'endpointName': 'xName'}],
	}
	return essential_fields


@pytest.fixture
def main_logger():
	return set_up_logger()


@pytest.fixture
def root_json_handler():
	yield JsonHandler(main_logger, VALID_JSON_PATH)


# Windows-specific tests
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_validate_essential_fields_command_script_disabled_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""
	Tests 'validate_essential_fields' method of class JSONHandler on Windows operating
	system, if the command script is not enabled.\n
	Tests the following cases:\n
	- 'enableCommandScriptWindows' is set to False\n
	- 'enableCommandScriptWindows' key is not in json file
	"""
	assert ENABLE_CS_W in json_essential_fields  # Ensure key exists
	print(ENABLE_CS_W in json_essential_fields)
	root_json_handler.validate_file()
	message = (
		f'400: Command script execution is disabled in the configuration file. '
		f'Set field {ENABLE_CS_W} to True'
	)
	with pytest.raises(HTTPException, match=message):
		json_essential_fields.__setitem__('enableCommandScriptWindows', False)
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message):
		del json_essential_fields['enableCommandScriptWindows']
		root_json_handler.validate_essential_fields(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_validate_essential_fields_command_script_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler on Windows operating
	system, if the command script is missing.\n Tests the following cases:\n
	- 'commandScriptWindows' is set to False\n
	- 'commandScriptWindows' key is not in json file
	"""
	root_json_handler.validate_file()
	message = (
		f'Command script not specified in the configuration file. ' f'Please add the key "{CS_W}".'
	)
	with pytest.raises(HTTPException, match=message):
		json_essential_fields.__setitem__('commandScriptWindows', '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message):
		del json_essential_fields['commandScriptWindows']
		root_json_handler.validate_essential_fields(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_windows_validate_essential_fields_tool_dir_missing_error(
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
def test_windows_validate_essential_fields_launch_settings_missing_error(
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
