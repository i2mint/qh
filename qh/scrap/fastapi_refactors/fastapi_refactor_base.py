"""A simple fastAPI app, to be refactored"""

from typing import Callable, MutableMapping
from dataclasses import dataclass

URI_TYPE = str
StoreFactory = Callable[[URI_TYPE], MutableMapping]


def random_integer(smallest: int = 1, highest: int = 10):
    """Return a random integer between smallest and highest"""
    from random import randint

    return randint(smallest, highest)


def greeter(greeting: str = 'Hello', name: str = 'world', n: int = 1):
    """Return a greeting"""
    return '\n'.join(f"{greeting}, {name}!" for _ in range(n))


# a dict with two users, each having 2 or 3 named "stores" (dicts)
backend_mall = {
    "alice": {
        'fruit': {"apple": 1, "banana": 2},
        'planets': {"mercury": 10, "venus": 20, "earth": 30},
    },
    "bob": {
        'food': {"apple": 1, "broccoli": 2, "carrot": 3},
        'cars': {"ford": 10, "toyota": 20},
        'colors': {'red': 100},
    },
}


def get_store(user: str):
    return backend_mall[user]



# -------------------------------------------------------------------------------------
# Ignore for now

DFLT_URI = 'test_uri'


def test_uri_to_store(uri: str = DFLT_URI):
    assert uri == DFLT_URI, f"Can only use uri={DFLT_URI} for now..."
    return backend_mall


@dataclass
class StoreAccess:
    """
    Delegator for MutableMapping, providing list, read, write, and delete methods.

    This is intended to be used in web services, offering nicer method names than
    the MutableMapping interface, and an actual list instead of a generator in
    the case of list.

    >>> s = StoreAccess.from_uri('test_uri')
    >>> s.list()
    ['alice', 'bob']

    """

    store: MutableMapping

    @classmethod
    def from_uri(cls, uri: URI_TYPE = DFLT_URI):
        """code that makes a MutableMapping interface for the data pointed to by uri"""
        if uri == DFLT_URI:
            store = backend_mall
            return cls(store)
        else:
            raise ValueError(f"Only one possible uri for now: {DFLT_URI}")

    def list(self):
        return list(self.store.keys())

    def read(self, key):
        return self.store[key]

    def write(self, key, value):
        self.store[key] = value

    def delete(self, key):
        del self.store[key]
