import multiprocessing

import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def read_root():
	return {'Hello': 'World'}


if __name__ == '__main__':
	multiprocessing.freeze_support()  # For Windows support
	uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True, workers=1)
