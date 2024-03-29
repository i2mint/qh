"""Testing store dispatching"""

from fastapi.testclient import TestClient


def test_store_dispatch(app):
    from time import sleep

    client = TestClient(app)

    response = client.get("/list/test_uri")
    assert response.status_code == 200
    assert response.json() == ["test_key", "test_key_2", "test_key_3"]

    response = client.get("/read/test_uri/test_key")
    assert response.status_code == 200
    assert response.json() == "test_value"

    data = {"key": "test_key", "value": "test_value_new"}
    response = client.post("/write/test_uri", json=data)
    assert response.status_code == 200
    assert response.json() == {"message": "Value written successfully"}

    # sleep(1)

    response = client.get("/read/test_uri/test_key")
    assert response.status_code == 200
    assert response.json() == "test_value_new"  # new value!

    # DELETE

    response = client.delete("/delete/test_uri/test_key")
    assert response.status_code == 200
    # assert response.json() == {"message": "Key deleted successfully"}

    # sleep(1)

    response = client.get("/list/test_uri")
    assert response.status_code == 200
    # no more rest_key: Only the two other keys
    assert response.json() == ["test_key_2", "test_key_3"]


from qh.scrap.store_dispatch_1 import app
from qh.scrap.store_dispatch_2 import app


test_store_dispatch(app)
