from unittest.mock import patch

import pytest
from fastapi import HTTPException

from rest_rce.src.constants import CS_L, ENABLE_CS_L, VALID_JSON_PATH
from rest_rce.src.json_handler import JsonHandler
from rest_rce.src.main import set_up_logger


# Pytest fixtures
@pytest.fixture
def json_essential_fields():
	essential_fields = {
		'enableCommandScriptLinux': True,
		'commandScriptLinux': 'xyz',
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


# Linux-specific tests
@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_linux_validate_essential_fields_command_script_disabled_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""
	Tests 'validate_essential_fields' method of class JSONHandler on Ubuntu operating
	system, if the command script is not enabled.\n
	Tests the following cases:\n
	- 'enableCommandScriptLinux' is set to False\n
	- 'enableCommandScriptLinux' key is not in json file
	"""
	root_json_handler.validate_file()
	message = (
		f'400: Command script execution is disabled in the configuration file. '
		f'Set field {ENABLE_CS_L} to True'
	)
	with pytest.raises(HTTPException, match=message):
		json_essential_fields.__setitem__(ENABLE_CS_L, False)
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message):
		del json_essential_fields[ENABLE_CS_L]
		root_json_handler.validate_essential_fields(json_essential_fields)


@patch('rest_rce.src.json_handler.JsonHandler.validate_schema', return_value=None)
def test_linux_validate_essential_fields_command_script_missing_error(
	mock_validate_schema, root_json_handler, json_essential_fields
):
	"""Tests 'validate_essential_fields' method of class JSONHandler on Ubuntu operating
	system, if the command script is missing.\n Tests the following cases:\n
	- 'commandScriptLinux' is set to False\n
	- 'commandScriptLinux' key is not in json file
	"""
	root_json_handler.validate_file()
	message = (
		f'Command script not specified in the configuration file. Please add the key "{CS_L}".'
	)
	with pytest.raises(HTTPException, match=message):
		json_essential_fields.__setitem__(CS_L, '')
		root_json_handler.validate_essential_fields(json_essential_fields)
	with pytest.raises(HTTPException, match=message):
		del json_essential_fields[CS_L]
		root_json_handler.validate_essential_fields(json_essential_fields)
