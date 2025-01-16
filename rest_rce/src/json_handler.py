import json
import os


class JsonHandler:
	def __init__(self, file_path):
		self.file_path = file_path

	def validate_file(self):
		if not self.file_path.endswith('.json'):
			raise ValueError(f'Invalid file type: {self.file_path}. Expected a .json file.')

		if not os.path.exists(self.file_path):
			raise FileNotFoundError(f"The file '{self.file_path}' does not exist.")

		try:
			with open(self.file_path) as file:
				json.load(file)
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid JSON syntax in file '{self.file_path}': {e}") from e
		# return a success message if nothing failed
		return f"File with path '{self.file_path}' is a valid JSON file."
