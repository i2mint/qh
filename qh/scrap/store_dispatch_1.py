"""Dispatching a store"""

from dataclasses import dataclass
from collections.abc import MutableMapping

backend_test_data = {'test_key': 'test_value', 'test_key_2': 2, 'test_key_3': [1, 2, 3]}


@dataclass
class StoreAccess:
    """
    Delegator for MutableMapping, providing list, read, write, and delete methods.

    This is intended to be used in web services, offering nicer method names than
    the MutableMapping interface, and an actual list instead of a generator in
    the case of list.
    """

    store: MutableMapping

    @classmethod
    def from_uri(cls, uri: str = 'test_uri'):
        """code that makes a MutableMapping interface for the data pointed to by uri"""
        if uri == 'test_uri':
            data = backend_test_data
            return cls(data)

    def list(self):
        return list(self.store.keys())

    def read(self, key):
        return self.store[key]

    def write(self, key, value):
        self.store[key] = value

    def delete(self, key):
        del self.store[key]


from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/list/{uri}")
async def list_keys(uri: str):
    store = StoreAccess.from_uri(uri)
    return store.list()


@app.get("/read/{uri}/{key}")
async def read_key(uri: str, key: str):
    try:
        store = StoreAccess.from_uri(uri)
        return store.read(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Key not found")


# This didn't work for me:
# @app.post("/write/{uri}")
# async def write_key(
#     uri: str, key: str, value: str
# ):  # Adjust value type based on your use case
#     store = StoreAccess.from_uri(uri)
#     store.write(key, value)
#     return {"message": "Value written successfully"}

# Had to make a model:
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel


# Define a Pydantic model for the request body
class WriteRequestBody(BaseModel):
    key: str
    value: str  # Adjust the type according to your needs


@app.post("/write/{uri}")
async def write_key(uri: str, body: WriteRequestBody):
    store = StoreAccess.from_uri(uri)
    store.write(body.key, body.value)
    return {"message": "Value written successfully"}


@app.delete("/delete/{uri}/{key}")
async def delete_key(uri: str, key: str):
    try:
        store = StoreAccess.from_uri(uri)
        store.delete(key)
        return {"message": "Key deleted successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Key not found")
