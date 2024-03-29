"""A simple fastAPI app, to be refactored"""

from fastapi import FastAPI
from typing import Any

# Assuming these are defined elsewhere
from qh.scrap.fastapi_refactors.fastapi_refactor_base import (
    random_integer,
    greeter,
    get_store,
)

app = FastAPI()


# Function definitions remain the same
def get_random_integer():
    return random_integer()


def greet(greeting: str, name: str):
    return greeter(greeting, name)


def get_store_list(user: str):
    store = get_store(user)
    return list(store)


def get_store_value(user: str, key: str):
    store = get_store(user)
    return store[key]


def set_store_value(user: str, key: str, value: Any):
    store = get_store(user)
    store[key] = value
    return {"message": "Value set successfully"}


# Configurations for each endpoint
configs = {
    get_random_integer: {"method": 'get', "endpoint": "/random_integer"},
    greet: {"method": 'get', "endpoint": "/greeter/{greeting}/{name}"},
    get_store_list: {"method": 'get', "endpoint": "/store_list/{user}"},
    get_store_value: {"method": 'get', "endpoint": "/store_get/{user}/{key}"},
    set_store_value: {"method": 'post', "endpoint": "/store_set/{user}/{key}"},
}

# Applying decorators dynamically based on the configs
for function, config in configs.items():
    if config['method'] == 'get':
        app.get(config['endpoint'])(function)
    elif config['method'] == 'post':
        app.post(config['endpoint'])(function)
