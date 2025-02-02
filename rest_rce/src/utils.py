import argparse
import logging
import os
import sys
from contextvars import ContextVar


def parse_arguments() -> tuple[str, float, int]:
	"""Parse arguments given via the command line."""
	parser = argparse.ArgumentParser(description='Process some inputs.')
	# Required argument config file path
	parser.add_argument('config_file_path', type=str, help='Path to the config file')
	# Optional arguments
	parser.add_argument(
		'-t', '--timeout', type=float, help='Timeout value in minutes', default=None
	)
	parser.add_argument(
		'-r', '--request_limit', type=int, help='Request limit for parallel processes', default=10
	)
	args = parser.parse_args()
	config_file_path = args.config_file_path
	timeout = args.timeout
	limit = args.request_limit
	return config_file_path, timeout, limit


def set_up_logger(request_id_var: ContextVar[str]) -> logging.Logger:
	"""Set up logger for rest api containing file and console handlers."""
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	formatter = logging.Formatter(
		'%(asctime)s - %(levelname)s - [Request ID: %(request_id)s] - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S',
	)

	class ContextFilter(logging.Filter):
		"""Logging filter to add request_id to log records."""

		def filter(self, record):
			request_id = request_id_var.get()
			record.request_id = request_id if request_id else 'SYSTEM'
			return True

	# Define a fixed log directory inside the project root
	start_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of the current script
	repo_root = find_project_directory(start_dir)
	log_dir = os.path.join(repo_root, 'logs')
	os.makedirs(log_dir, exist_ok=True)
	log_file_path = os.path.join(log_dir, 'tool_execution.log')

	log_file_handler = logging.FileHandler(log_file_path)
	log_file_handler.setFormatter(formatter)
	log_file_handler.addFilter(ContextFilter())

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	console_handler.addFilter(ContextFilter())

	logger.addHandler(log_file_handler)
	logger.addHandler(console_handler)

	return logger


def find_project_directory(start_dir):
	"""Find the project directory by recursively searching for a pyproject.toml file
	starting from a given directory."""
	current_dir = start_dir
	while current_dir:
		if os.path.exists(os.path.join(current_dir, 'pyproject.toml')):
			return current_dir
		parent_dir = os.path.dirname(current_dir)
		if parent_dir == current_dir:  # Reached the root directory
			break
		current_dir = parent_dir
	return None


def run_parse_arguments(mock_args, monkeypatch):
	"""Helper function to run parse_arguments with mocked sys.argv."""
	monkeypatch.setattr(sys, 'argv', mock_args)
	return parse_arguments()


def assert_output_values(res, expected_out):
	"""Helper function to validate the response from the tool execution."""
	assert res.status_code == 200, f'Unexpected status {res.status_code}: {res.json()}'

	res_json = res.json()

	assert 'stdout' in res_json, f'Missing stdout in response: {res_json}'
	assert 'command' in res_json, f'Missing command in response: {res_json}'
	assert 'output_variables' in res_json, f'Missing output_variables in response: {res_json}'

	# Compare command and output values
	expected_stdout, response_stdout = expected_out['stdout'], res_json['stdout']
	assert (
		response_stdout == expected_stdout
	), f'Command mismatch: expected {expected_stdout}, got {response_stdout}'
	expected_c, response_c = expected_out['command'], res_json['command']
	assert response_c == expected_c, f'Command mismatch: expected {expected_c}, got {response_c}'
	expected_ov, response_ov = expected_out['output_variables'], res_json['output_variables']
	assert response_ov == expected_ov, f'Output mismatch: expected {expected_ov}, got {response_ov}'
