"""
Simple example of qh.

Run this script somewhere, and try things like:

```
curl http://127.0.0.1:8080/ping
# should get {"ping": "pong"}

curl -X POST http://127.0.0.1:8080/poke
# should get "here is a peek"

curl -H "Content-Type: application/json" -X POST -d '{"x": 3}' http://127.0.0.1:8080/foo
# (should get 5)

curl -H "Content-Type: application/json" -X POST -d '{"name": "qh"}' http://127.0.0.1:8080/bar
# should get "hello qh!"

curl -H "Content-Type: application/json" -X POST -d '{"a": [1,2,3], "b": [4,5,6]}' http://127.0.0.1:8080/add_numpy_arrays
# should get [5, 7, 9]
```

"""
from qh import mk_http_service_app


def poke():
    return 'here is a peek'


def foo(x: int):
    return x + 2


def bar(name='world'):
    return f"Hello {name}!"


# To deploy the above, we would just need to do
#   `app = mk_http_service_app([poke, foo, bar])

# But check out this one:

def add_numpy_arrays(a, b):
    return (a + b).tolist()


# Here the a and b are assumed to be numpy arrays (or .tolist() would fail).
# Out of the box, qh can only handle json types (str, list, int, float), so we need to preprocess the input.
# qh makes that easy too.
# Here we provide a name->conversion_func mapping (but could express it otherwise)

from qh.trans import mk_json_handler_from_name_mapping
import numpy as np

input_trans = mk_json_handler_from_name_mapping(
    {
        "a": np.array,
        "b": np.array
    }
)

app = mk_http_service_app([poke, foo, bar, add_numpy_arrays],
                          input_trans=input_trans)

if __name__ == '__main__':
    app.run()  # note:  you can configure a bunch of stuff here (port, cors, etc.) but we're taking defaults
