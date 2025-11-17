# Notes for a future `qh` (and `py2http` perhaps). (#1)

We're going to use `qh`, which is not heavily used, as a place to develop a new `py2http` (which is used more, but is getting fatigue). Here are some notes for this.


## Comment

## Dispatching a store

Yes -- dispatching a function is the fundamental thing with which you can do all the rest. 
Yes -- dispatching a general object might be more fundamental (since a function is just an instance object with a `__call__`). 
But right now, we want to start with something immediately useful to us, and quite powerful, as well as illustrative of the power we'll get with `qh`: Dispatching a store.

### The problem

I'd like to be able to wrap data access functionality into http services easily. 
Essentially say "here's my store (factory), and here's the methods I want to expose/dispatch as a web service", and get all the necessary endpoints for that.
I'd like to do so using FastAPI, without facading it, so we can get this up on it's feet quickly. 

On the backend I have an object that wraps a Mapping like this:

```python
from dataclasses import dataclass
from typing import MutableMapping

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
    def from_uri(cls, uri: str):
       """code that makes a MutableMapping interface for the data pointed to by uri"""

    def list(self):
        return list(self.store.keys())

    def read(self, key):
        return self.store[key]

    def write(self, key, value):
        self.store[key] = value

    def delete(self, key):
        del self.store[key]
```

I'd like to use FastAPI to make a webservice for this, which has four endpoints, one for each of the methods (list, read, write and delete). These should take the uri, as well as the other relevant arguments when relevant (key and/or value), and run those methods. 
For example, for read, the backend would do `StoreAccess.from_uri(uri).read(key)`. 


### Elements of a solution

To create a web service with FastAPI that exposes the `StoreAccess` class methods as endpoints, you'll need to follow a series of steps. FastAPI is an excellent choice for this task due to its simplicity, performance, and ease of use for creating RESTful APIs. Below is a guide on how to achieve this, including the setup of FastAPI, defining the API endpoints, and integrating your `StoreAccess` class into these endpoints.

#### 1. Setup FastAPI

First, ensure you have FastAPI and Uvicorn (an ASGI server) installed in your environment. If not, you can install them using pip:

```bash
pip install fastapi uvicorn
```

#### 2. Define Your FastAPI App

Create a new Python file for your FastAPI application, for example, `main.py`, and import FastAPI along with your `StoreAccess` class.

```python
from fastapi import FastAPI, HTTPException
from yourmodule import StoreAccess  # Ensure this points to where your StoreAccess class is defined.

app = FastAPI()
```

#### 3. Create Endpoints

You'll define four endpoints corresponding to the methods in your `StoreAccess` class (`list`, `read`, `write`, and `delete`). Each endpoint will accept different parameters as needed.

##### List Endpoint

```python
@app.get("/list/{uri}")
async def list_keys(uri: str):
    store = StoreAccess.from_uri(uri)
    return store.list()
```

##### Read Endpoint

```python
@app.get("/read/{uri}/{key}")
async def read_key(uri: str, key: str):
    try:
        store = StoreAccess.from_uri(uri)
        return store.read(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Key not found")
```

##### Write Endpoint

```python
@app.post("/write/{uri}")
async def write_key(uri: str, key: str, value: str):  # Adjust value type based on your use case
    store = StoreAccess.from_uri(uri)
    store.write(key, value)
    return {"message": "Value written successfully"}
```

For the write endpoint, you might need to adjust how you accept the `value` parameter, depending on the expected data type and structure. FastAPI supports request bodies, which can be useful for passing JSON data.

##### Delete Endpoint

```python
@app.delete("/delete/{uri}/{key}")
async def delete_key(uri: str, key: str):
    try:
        store = StoreAccess.from_uri(uri)
        store.delete(key)
        return {"message": "Key deleted successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Key not found")
```

#### 4. Run Your FastAPI App

You can run your FastAPI app using Uvicorn. For example, if your FastAPI application is defined in `main.py`, you can start it with:

```bash
uvicorn main:app --reload
```

This command starts a local server on `http://127.0.0.1:8000` (by default), where you can access your endpoints. The `--reload` flag enables live reloading during development.

#### 5. Testing and Documentation

FastAPI automatically generates documentation for your API, accessible at `http://127.0.0.1:8000/docs` or `http://127.0.0.1:8000/redoc` when your server is running. You can use this documentation to test your endpoints directly from the browser.

#### Alternative Approaches and Considerations

- **Security and Authentication:** Depending on your application's needs, you might want to add authentication to protect your endpoints. FastAPI supports several ways to add security and authentication, such as OAuth2 with Password (and hashing), JWT tokens, and more.
- **Error Handling:** Improve error handling in your application to manage different exceptions gracefully, ensuring your API responds with appropriate HTTP status codes and messages.
- **Data Validation:** FastAPI supports Pydantic models for request body validation. You can define models for your write operations to ensure incoming data adheres to a specific structure and type.
- **Scalability:** As your application grows, consider structuring your FastAPI project using Routers and Dependencies for better maintainability and scalability.

By following these steps and considerations, you can create a robust web service with FastAPI that exposes your `StoreAccess` functionality through HTTP endpoints, offering a practical and efficient way to interact with your data store.


## Comment

## getting the routes from the app object

When we test an `app` (webservice object), we'd like to be able to get information on what routes are in it.
I don't know what it is for other frameworks, but with `azure.functions.FunctionApp`, there's no public API for this. 

So we could do this:

```python
def routes_of_app(app):
    """
    Yields (name, func) pairs for the routes of azure.functions app.
    (Note: Tested for `azure-functions==1.21.3`)
    """
    for route in app._function_builders:
        yield route._function._name, route._function._func

# example: 
# dict(routes_of_app(app))
```

That said, it's generally frowned upon to depend on non-public APIs. For a reason. We'd then have to maintain this routes_of_app function, and if it becomes hard, or impossible to retrieve the routes, we're in trouble. 

Another (considered more clean) possibility is to build our own "registration" mechanism, to accumulate the routes list/dict ourselves.
For example:

```python
registered_routes = {}

def register_route(route, methods):
    def decorator(func):
        # Register the function in your own registry.
        registered_routes[route] = {
            "methods": methods,
            "handler": func,
        }
        return func
    return decorator
```

Which would be used like this:

```python
import azure.functions as af

app = FunctionApp(http_auth_level=af.AuthLevel.ANONYMOUS)

@app.route(route="foo", methods=["GET"])
@register_route("foo", ["GET"])
def foo(req: af.HttpRequest) -> af.HttpResponse:
    ...
```

or to pack both decorators in one:

```python
import azure.functions as af
from azure.functions import FunctionApp

# Custom registry to keep track of routes and their handlers.
registered_routes = {}

def add_route(app: FunctionApp, route: str, methods: list, **kwargs):
    """
    A decorator that registers a route handler with both the FunctionApp
    and a custom registry.

    Args:
        app (FunctionApp): The Azure Functions app instance.
        route (str): The route path.
        methods (list): List of HTTP methods allowed (e.g., ["GET"] or ["GET", "POST"]).
        **kwargs: Any additional keyword arguments to pass to app.route.

    Returns:
        A decorator that registers the function with both the custom registry and the app.
    """
    def decorator(func_handler):
        # Add the route to the custom registry.
        registered_routes[route] = {
            "methods": methods,
            "handler": func_handler,
        }
        # Register the route using the standard app.route decorator.
        return app.route(route=route, methods=methods, **kwargs)(func_handler)
    return decorator
```

which could then be used like this:

```python

@add_route(app, route="foo", methods=["GET"])
def foo(req: func.HttpRequest) -> func.HttpResponse:
    ...
```



