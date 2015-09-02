from lib.fetch import Fetch
from lib.git_parse import GitHub
import os, nose, json, requests, requests_mock
from nose.tools import with_setup
from nose.plugins.skip import Skip, SkipTest

### Setup methods ###
def setup():
    if os.path.exists("/tmp/_data"):
        pass
    else:
        os.mkdir("/tmp/_data")

def teardown():
    if os.path.isfile('/tmp/_data/test.json'):
        os.remove("/tmp/_data/test.json")
    else:
        pass

### Fetch module tests ###

@with_setup(setup, teardown)
@requests_mock.mock()
def test_Fetch_get_data_from_url(m):
    f = Fetch('https://example.com')
    expected = dict()
    m.get("https://example.com", content=expected, status_code=200)
    actual = f.get_data_from_url()
    assert expected == actual

@with_setup(setup, teardown)
def test_Fetch_save_data():
    f = Fetch('https://example.com')
    data = dict(test="value")
    filename = "/tmp/_data/test.json"
    f.save_data(data, filename)
    assert os.path.isfile(filename)

@with_setup(setup, teardown)
def test_Fetch_save_data_w_str_expects_False():
    f = Fetch('https://example.com')
    data = str("value")
    filename = "/tmp/_data/test.json"
    assert f.save_data(data, filename) is False

@with_setup(setup, teardown)
def test_Fetch_get_data_from_file():
    f = Fetch("")
    data = dict(test="value")
    filename = "/tmp/_data/test.json"
    open(filename, 'w').write(json.dumps(data))
    target = f.get_data_from_file(filename)
    assert target == data

### GitHub Module tests ###

@requests_mock.mock()
def test_GitHub_fetch_raw(m):
    g = GitHub('18f.gsa.gov','18F')
    request_string = "18F/18f.gsa.gov/staging/go"
    url = "https://raw.githubusercontent.com/%s" % request_string
    m.get(url, content="Success!", status_code=200)
    actual = g.fetch_raw(request_string)
    assert actual.content == "Success!"

@requests_mock.mock()
def test_GitHub_fetch_raw_when_request_not_ok(m):
    g = GitHub('18f.gsa.gov','18F')
    request_string = "18F/18f.gsa.gov/staging/go.html"
    url = "https://raw.githubusercontent.com/18F/18f.gsa.gov/staging/go.html"
    m.get(url, status_code=418, text="I'm a teapot")
    actual = g.fetch_raw(request_string)
    assert actual is False

@requests_mock.mock()
def test_GitHub_fetch_endpoint_when_request_ok(m):
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "issues"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    m.get(url, content="", status_code=200, headers={'Content-Type':'text/html'})
    actual = g.fetch_endpoint(endpoint)
    assert actual.content is ""

@requests_mock.mock()
def test_GitHub_fetch_endpoint_when_request_not_ok(m):
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "nonexistentendpoint"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    m.get(url, content="", status_code=404, headers={'Content-Type':'text/html'})
    actual = g.fetch_endpoint(endpoint)
    assert actual is False

@requests_mock.mock()
def test_GitHub_fetch_commits_request_not_ok(m):
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "commits"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    m.get(url, content="", status_code=404, headers={'Content-Type':'text/html'})
    actual = g.fetch_commits()
    assert actual is False

@requests_mock.mock()
def test_GitHub_fetch_commits_request_ok(m):
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "commits"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    m.get(url, content='[{"name": "18f.gsa.gov"}]', status_code=200)
    actual = g.fetch_commits()
    assert actual == [{u'name': u'18f.gsa.gov'}]

@requests_mock.mock()
def test_GitHub_fetch_issues(m):
    g= GitHub('18f.gsa.gov', '18F')
    url = "%s/repos/%s/%s/issues?per_page=100" % (g.api, g.owner, g.repo)
    expected = [dict()]*100
    m.get(url, content=expected.__str__(), status_code=200, headers={'Content-Type': 'application/json'})
    actual = g.fetch_issues()
    assert actual == expected

@requests_mock.mock()
def test_GitHub_get_repo_contents(m):
    g = GitHub('18f.gsa.gov', '18f')
    url = 'https://api.github.com/repos/18f/18f.gsa.gov/contents/_posts'
    expected = "[{'name': '18f.gsa.gov'}]"
    m.get(url, content=expected, status_code=200, headers={'Content-Type': 'application/json'})
    actual = g.get_repo_contents('_posts')
    assert expected == actual

def test_GitHub_parse_by_key():
    g = GitHub('', '')
    expected = ['data-pull', 'data-push']
    data = [{"name":"data-push"},{"name":"data-pull"},{"name":"nondata-push"}]
    actual = g.parse_by_key(data, 'name', 'data')
    assert expected.sort() == actual.sort()
