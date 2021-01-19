
# qh
Quick Http web-service construction.

Getting from python to an http-service exposing them to the world, 
in the easiest way machinely possible.

Harnesses the great power of [py2http](https://github.com/i2mint/py2http) 
without all the responsibilities. 

This is meant for the desireable lightening fast development cycles during 
proof-of-conceptualization. 
As you move towards production, consider using one of those boring grown-up tools out there... 


To install:	```pip install qh```

# Examples

## When all goes as planned...

```python
import qh
from qh import mk_http_service_app

def poke():
    return 'here is a peek'

def foo(x: int):
    return x + 2

def bar(name='world'):
    return f"Hello {name}!"

app = mk_http_service_app([foo, bar, poke])
app.run()
```

```
Bottle v0.12.19 server starting up (using WSGIRefServer())...
Listening on http://127.0.0.1:8080/
Hit Ctrl-C to quit.
```

Now grab a browser and go to `http://127.0.0.1:8080/ping`...

```
{"ping": "pong"}
```

Now be happy (or go try the other function by doing some post requests).

Try ``http://127.0.0.1:8080/poke`...