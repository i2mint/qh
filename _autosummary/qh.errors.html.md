# qh.errors

What HTTP clients learn about server-side exceptions.

Exception messages routinely carry file paths, connection strings or fragments of
data, so by default a client only gets a generic message with an error id; the
full exception (with traceback) is logged server-side under that same id, so an
operator can find it from what the client reports.

`expose_errors=True` (on `qh.mk_app`, `qh.base.mk_fastapi_app`, …) restores
the old behaviour of sending the exception text to the client; use it for
development or when every client is trusted.

```pycon
>>> detail = error_detail(ValueError('/secret/path'), context='f')
>>> '/secret/path' in detail, detail.startswith('Internal error in f (error id: ')
(False, True)
>>> error_detail(ValueError('/secret/path'), context='f', expose_errors=True)
'Error in f: /secret/path'
```

### Functions

| [`error_detail`](#qh.errors.error_detail)(exc, \*, context[, ...])   | Log `exc` (with traceback) under a fresh error id and return the text to send to the client.   |
|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|

### qh.errors.error_detail(exc, , context, expose_errors=False, exposed_text=None)

Log `exc` (with traceback) under a fresh error id and return the text to
send to the client.

* **Parameters:**
  * **exc** ([`BaseException`](https://docs.python.org/3/builtins/exceptions.html#BaseException)) – The exception raised while serving the request.
  * **context** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – What failed (typically the function name); shown to the client.
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, the client gets the exception text.
  * **exposed_text** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The client-facing text when `expose_errors` is True;
    defaults to `f"Error in {context}: {exc}"`.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
