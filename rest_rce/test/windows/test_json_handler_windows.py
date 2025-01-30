from unittest.mock import patch

import pytest
from fastapi import HTTPException

from rest_rce.src.constants import CS_W, ENABLE_CS_W, VALID_JSON_PATH
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
	root_json_handler.validate_file()
	message = (
		f'400: Command script execution is disabled in the configuration file. '
		f'Set field {ENABLE_CS_W} to True'
	)
	with pytest.raises(HTTPException, match=message), patch('os.name', 'nt'):
		json_essential_fields.__setitem__(ENABLE_CS_W, False)
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message), patch('os.name', 'nt'):
		del json_essential_fields[ENABLE_CS_W]
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
		f'Command script not specified in the configuration file. Please add the key "{CS_W}".'
	)
	with pytest.raises(HTTPException, match=message), patch('os.name', 'nt'):
		json_essential_fields.__setitem__(CS_W, '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message), patch('os.name', 'nt'):
		del json_essential_fields[CS_W]
		root_json_handler.validate_essential_fields(json_essential_fields)
