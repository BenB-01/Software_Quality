import multiprocessing
import uvicorn
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from json_handler import JsonHandler

app = FastAPI()


@app.get('/')
def read_root():
	return {'Hello': 'World'}


@app.post("/execute-tool/")
async def execute_tool(config_file: UploadFile = File(...)):
	"""Endpoint to upload a configuration.json file and execute a tool in RCE."""

	filename = {"filename": config_file.filename}

	# Save uploaded file temporarily
	temp_path = f"./{config_file.filename}"
	with open(temp_path, "wb") as f:
		content = await config_file.read()
		f.write(content)

	try:
		# Validate the JSON file using JsonHandler
		json_handler = JsonHandler(temp_path)
		response = json_handler.validate_file()
		return {"temp_path": temp_path, "response": response, "filename": filename}

	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	finally:
		# Clean up temporary file
		if os.path.exists(temp_path):
			os.remove(temp_path)


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run(app, host='127.0.0.1', port=8000, reload=False, workers=1)
