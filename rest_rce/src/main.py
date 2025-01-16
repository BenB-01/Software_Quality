import multiprocessing
import uvicorn
import os
import logging
import subprocess
from fastapi import FastAPI, UploadFile, File, HTTPException
from json_handler import JsonHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get('/')
def read_root():
	return {'Hello': 'World'}


@app.post("/execute-tool/")
async def execute_tool(config_file: UploadFile = File(...)):
	"""Endpoint to upload a configuration.json file and execute a tool in RCE."""

	set_tool_dir, tool_directory = False, ""
	start_working_dir = os.getcwd()

	# Save uploaded file temporarily
	temp_path = f"./{config_file.filename}"
	with open(temp_path, "wb") as f:
		content = await config_file.read()
		f.write(content)

	try:
		# Validate JSON file and extract values using JsonHandler
		json_handler = JsonHandler(temp_path)
		response = json_handler.validate_file()
		command_script, set_tool_dir, tool_directory, inputs = json_handler.extract_values()

		input_values = {}
		for inp in inputs:
			endpoint_name = inp.get("endpointName")
			input_values[endpoint_name] = inp.get("endpointValue", 0)  # Default to 0 if no value is provided

		for key, value in input_values.items():
			command_script = command_script.replace(f"${{in:{key}}}", str(value))

		# Change working directory if needed
		if set_tool_dir and tool_directory:
			os.chdir(tool_directory)
			logger.info(f"Working directory changed to {tool_directory}.")

		# Execute the tool command
		process = subprocess.run(command_script, shell=True, capture_output=True, text=True)
		stdout = process.stdout
		stderr = process.stderr

		if process.returncode != 0:
			raise HTTPException(status_code=500, detail=f"Tool execution failed: {stderr}")

		# Return the results
		return {
			"response": response,
			"stdout": stdout,
			"tool_directory": tool_directory,
			"command": command_script,
		}

	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	finally:
		# Clean up temporary file
		if set_tool_dir and tool_directory:
			os.chdir(start_working_dir)
		if os.path.exists(temp_path):
			os.remove(temp_path)
		else:
			logger.warning(f"Temporary file {temp_path} not found for cleanup")


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)
