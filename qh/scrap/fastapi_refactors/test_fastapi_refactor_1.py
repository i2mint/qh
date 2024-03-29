from fastapi.testclient import TestClient

from qh.scrap.fastapi_refactors.fastapi_refactor_1 import app as default_app
from qh.scrap.fastapi_refactors.fastapi_refactor_base import backend_mall


def test_fastapi_refactor_app(app=default_app):

    client = TestClient(app)

    def test_get_random_integer():
        response = client.get("/random_integer")
        assert response.status_code == 200
        assert isinstance(response.json(), int)

    def test_greet():
        response = client.get("/greeter/Hi/John")
        assert response.status_code == 200
        assert response.json() == "Hi, John!", f"Got: {response.json()=}"

    def test_get_store_list():
        user = next(iter(backend_mall))
        keys = sorted(backend_mall[user].keys())

        response = client.get(f"/store_list/{user}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert response.json() == keys, f"Got: {response.json()=}"

    def test_get_store_value():
        user = next(iter(backend_mall))
        keys = sorted(backend_mall[user].keys())
        key = keys[0]
        value = backend_mall[user][key]

        response = client.get(f"/store_get/{user}/{key}")
        assert response.status_code == 200
        assert response.json() == value, f"Got: {response.json()=}"

    def test_set_store_value():
        user = next(iter(backend_mall))
        keys = sorted(backend_mall[user].keys())
        key = keys[0]

        response = client.post("/store_set/user1/key1", json={"value": "some_value"})
        assert response.status_code == 200
        assert response.json() == {"message": "Value set successfully"}
        assert backend_mall[user][key] == "some_value"
        # clean up (TODO: do with with block instead)
        del backend_mall[user][key]

    test_get_random_integer()
    test_greet()
    test_get_store_list()
    test_get_store_value()
