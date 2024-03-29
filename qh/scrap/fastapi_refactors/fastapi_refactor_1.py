"""A simple fastAPI app, to be refactored"""

from typing import Any
from fastapi import FastAPI
from typing import Any
from qh.scrap.fastapi_refactors.fastapi_refactor_base import (
    random_integer,
    greeter,
    get_store,
)


app = FastAPI()


store_getter = get_store


@app.get("/random_integer")
def get_random_integer():
    return random_integer()


@app.get("/greeter/{greeting}/{name}")
def greet(greeting: str, name: str):
    return greeter(greeting, name)


@app.get("/store_list/{user}")
def get_store_list(user: str):
    store = store_getter(user)

    return list(store)


@app.get("/store_get/{user}/{key}")
def get_store_value(user: str, key: str):
    store = store_getter(user)
    return store[key]


@app.post("/store_set/{user}/{key}")
def set_store_value(user: str, key: str, value: Any):
    store = store_getter(user)
    store[key] = value
    return {"message": "Value set successfully"}
