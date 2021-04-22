import sys
import os
import wget
import mimetypes
sys.path.insert(0, os.path.realpath(os.path.pardir))
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from celery_tasks.tasks import predict_image, predict_video
from celery.result import AsyncResult
from models import Task, Prediction
import uuid
import logging
from pydantic.typing import List, Optional
import numpy as np

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static/results'

isdir = os.path.isdir(UPLOAD_FOLDER)
if not isdir:
    os.makedirs(UPLOAD_FOLDER)

isdir = os.path.isdir(STATIC_FOLDER)
if not isdir:
    os.makedirs(STATIC_FOLDER)

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post('/api/process')
async def process(files: Optional[List[UploadFile]] = File(None), url: Optional[str] = Form(None)):
    tasks = []
    try:
        if files is None and url is None:
            raise Exception('No input found')

        if files is not None:
            for file in files:
                d = {}
                try:
                    name = str(uuid.uuid4()).split('-')[0]
                    ext = file.filename.split('.')[-1]
                    file_name = f'{UPLOAD_FOLDER}/{name}.{ext}'
                    # start task prediction
                    # Check file type (image or video)
                    # TODO: other cases
                    mimestart = mimetypes.guess_type(file_name)[0]
                    if mimestart is not None:
                        mimestart = mimestart.split('/')[0]
                        if mimestart in ('video', 'image'):
                            with open(file_name, 'wb+') as f:
                                f.write(file.file.read())
                            f.close()

                            if mimestart == 'image':
                                task_id = predict_image.delay(os.path.join('api', file_name))
                                d['task_id'] = str(task_id)
                                d['status'] = 'PROCESSING'
                                d['url_result'] = f'/api/result/{task_id}'
                            elif mimestart == 'video':
                                task_id = predict_video.delay(os.path.join('api', file_name))
                                d['task_id'] = str(task_id)
                                d['status'] = 'PROCESSING'
                                d['url_result'] = f'/api/result/{task_id}'
                except Exception as ex:
                    logging.info(ex)
                    d['task_id'] = str(task_id)
                    d['status'] = 'ERROR'
                    d['url_result'] = ''
                tasks.append(d)
        elif url is not None:
            d = {}
            try:
                path = wget.download(url, out=f'{UPLOAD_FOLDER}')
                print('path', path)
                mimestart = mimetypes.guess_type(path)[0]
                if mimestart is not None:
                    mimestart = mimestart.split('/')[0]
                    if mimestart == 'image':
                        task_id = predict_image.delay(os.path.join('api', path))
                        d['task_id'] = str(task_id)
                        d['status'] = 'PROCESSING'
                        d['url_result'] = f'/api/result/{task_id}'
                    elif mimestart == 'video':
                        task_id = predict_video.delay(os.path.join('api', path))
                        d['task_id'] = str(task_id)
                        d['status'] = 'PROCESSING'
                        d['url_result'] = f'/api/result/{task_id}'
            except Exception as ex:
                logging.info(ex)
                d['task_id'] = str(task_id)
                d['status'] = 'ERROR'
                d['url_result'] = ''
            tasks.append(d)
        
        return JSONResponse(status_code=202, content=tasks)
    except Exception as ex:
        logging.info(ex)
        return JSONResponse(status_code=400, content=[])


@app.get('/api/result/{task_id}', response_model=Prediction)
async def result(task_id: str):
    task = AsyncResult(task_id)

    # Task Not Ready
    if not task.ready():
        return JSONResponse(status_code=202, content={'task_id': str(task_id), 'status': task.status, 'result': ''})

    # Task done: return the value
    task_result = task.get()
    result = task_result.get('result')
    return JSONResponse(status_code=200, content={'task_id': str(task_id), 'status': task_result.get('status'), 'result': result})


@app.get('/api/status/{task_id}', response_model=Prediction)
async def status(task_id: str):
    task = AsyncResult(task_id)
    return JSONResponse(status_code=200, content={'task_id': str(task_id), 'status': task.status, 'result': ''})
