from lib.fetch import Fetch
from lib.git_parse import GitHub
import os, nose, json
from nose.tools import with_setup
import responses

def Fetch_setup():
    if os.path.exists("/tmp/_data"):
        pass
    else:
        os.mkdir("/tmp/_data")

def Fetch_teardown():
    if os.path.isfile('/tmp/_data/test.json'):
        os.remove("/tmp/_data/test.json")
    else:
        pass

### Fetch module tests ###

@responses.activate
@with_setup(Fetch_setup, Fetch_teardown)
def test_Fetch_get_data_from_url():
    f = Fetch('https://example.com')
    expected = dict()
    responses.add(responses.GET, 'https://example.com',
        body="{}",
        content_type="application/json")

    actual = f.get_data_from_url()

    assert expected == actual

@with_setup(Fetch_setup, Fetch_teardown)
def test_Fetch_save_data():
    f = Fetch('https://example.com')
    data = dict(test="value")
    filename = "/tmp/_data/test.json"
    f.save_data(data, filename)
    assert os.path.isfile(filename)

@with_setup(Fetch_setup, Fetch_teardown)
def test_Fetch_save_data_w_str_expects_False():
    f = Fetch('https://example.com')
    data = str("value")
    filename = "/tmp/_data/test.json"
    assert f.save_data(data, filename) is False

@with_setup(Fetch_setup, Fetch_teardown)
def test_Fetch_get_data_from_file():
    f = Fetch("")
    data = dict(test="value")
    filename = "/tmp/_data/test.json"
    open(filename, 'w').write(json.dumps(data))
    target = f.get_data_from_file(filename)
    assert target == data

### GitHub Module tests ###
@responses.activate
def test_GitHub_fetch_raw():
    g = GitHub('18f.gsa.gov','18F')
    request_string = "18F/18f.gsa.gov/staging/go"
    url = "https://raw.githubusercontent.com/%s" % request_string
    responses.add(responses.GET,
        url,
        body="Success!",
        content_type="text/html")
    actual = g.fetch_raw(request_string)
    assert actual.content == "Success!"

@responses.activate
def test_GitHub_fetch_raw_when_request_not_ok():
    g = GitHub('18f.gsa.gov','18F')
    request_string = "18F/18f.gsa.gov/staging/go"
    url = "https://raw.githubusercontent.com/18F/18f.gsa.gov/staging/go"
    responses.add(
        responses.GET, url,
        body='',
        status=404,
        content_type="text/html")
    actual = g.fetch_raw(request_string)
    assert actual is False

@responses.activate
def test_GitHub_get_repo_contents():
    g = GitHub('18f.gsa.gov', '18F')
    if g.user is None:
        g.user == "sample_key"
    expected = "[{'name': '18f.gsa.gov'}]"
    responses.add(
        responses.GET,
        'https://api.github.com/repos/18f/18f.gsa.gov/contents/_posts',
        body="[{'name': '18f.gsa.gov'}]",
        content_type="application/json")
    actual = g.get_repo_contents('_posts')
    import pdb; pdb.set_trace()

    assert expected == actual

def test_GitHub_parse_by_key():
    g = GitHub('', '')
    expected = ['data-pull', 'data-push']
    data = [{"name":"data-push"},{"name":"data-pull"},{"name":"nondata-push"}]
    actual = g.parse_by_key(data, 'name', 'data')
    assert expected.sort() == actual.sort()
