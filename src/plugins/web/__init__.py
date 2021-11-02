from fastapi.middleware.cors import CORSMiddleware
from .router import *


origins = [
    'http://localhost:8081'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*']
)
