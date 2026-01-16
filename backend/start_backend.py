from typing import Union

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/auth")
def get_auth():
    return {"message": "Authentication endpoint", "status": "active"}


@app.get("/login")
def get_login():
    return {"message": "Please provide your credentials to login"}