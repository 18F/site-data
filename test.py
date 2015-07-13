from lib.fetch import Fetch
import os, nose
from nose.tools import with_setup
import responses

def setup_func():
    if os.path.exists("tests/_data"):
        pass
    else:
        os.mkdir("tests/_data")

def teardown_func():
    if os.path.isfile('tests/_data/test.json'):
        os.remove("tests/_data/test.json")
    else:
        pass

@responses.activate
@with_setup(setup_func, teardown_func)
def test_Fetch_get_authors_from_url():
    f = Fetch('https://example.com')
    expected = dict()
    responses.add(responses.GET, 'https://example.com',
        body="{}",
        content_type="application/json")

    actual = f.get_authors_from_url()

    assert expected == actual

@with_setup(setup_func, teardown_func)
def test_Fetch_save_authors():
    f = Fetch('https://example.com')
    data = dict(test="value")
    filename = "tests/_data/test.json"
    f.save_authors(data, filename)
    assert os.path.isfile(filename)
