from lib.fetch import Fetch
from lib.git_parse import GitHub
import os, nose, json, requests, requests_mock
from nose.tools import with_setup
import responses
_globals = dict()
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
def issues_setup():
    _globals['testingdata'] = {x.__str__():x**2 for x in range(0,100)}

def issues_teardown():
    _globals['testingdata'] = None

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
    request_string = "18F/18f.gsa.gov/staging/go.html"
    url = "https://raw.githubusercontent.com/18F/18f.gsa.gov/staging/go.html"
    responses.add(
        responses.GET, url,
        body='',
        status=404,
        content_type="text/html")
    actual = g.fetch_raw(request_string)
    assert actual is False

@responses.activate
def test_GitHub_fetch_endpoint_when_request_ok():
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "issues"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    responses.add(
        responses.GET, url,
        body='',
        status=200,
        content_type="text/html")
    actual = g.fetch_endpoint(endpoint)
    assert actual is not False

@responses.activate
def test_GitHub_fetch_endpoint_when_request_not_ok():
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "nonexistentendpoint"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    responses.add(
        responses.GET, url,
        body='',
        status=404,
        content_type="text/html")
    actual = g.fetch_endpoint(endpoint)
    assert actual is False

@responses.activate
def test_GitHub_fetch_commits_request_not_ok():
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "commits"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    responses.add(
        responses.GET, url,
        body='',
        status=404,
        content_type="text/html")
    actual = g.fetch_commits()
    assert actual is False

@responses.activate
def test_GitHub_fetch_commits_request_ok():
    g = GitHub('18f.gsa.gov','18F')
    endpoint = "commits"
    url = "%s/repos/%s/%s/%s" % (g.api, g.owner, g.repo, endpoint)
    responses.add(
        responses.GET, url,
        body='[{"name": "18f.gsa.gov"}]',
        status=200,
        content_type="application/json")
    actual = g.fetch_commits()
    assert actual == [{u'name': u'18f.gsa.gov'}]

def test_GitHub_fetch_issues():
    g= GitHub('18f.gsa.gov', '18F')
    url = "%s/repos/%s/%s/issues?per_page=100" % (g.api, g.owner, g.repo)
    session = requests.Session()
    adapter = requests_mock.Adapter()
    session.mount('mock', adapter)
    adapter.register_uri('GET', url, text='data')
    issues = g.fetch_issues()
    assert issues is not False

@responses.activate
def test_GitHub_get_repo_contents():
    g = GitHub('18f.gsa.gov', '18f')
    if g.user is None:
        g.user == "sample_key"
    expected = "[{'name': '18f.gsa.gov'}]"
    responses.add(
        responses.GET,
        'https://api.github.com/repos/18f/18f.gsa.gov/contents/_posts',
        body="[{'name': '18f.gsa.gov'}]",
        content_type="application/json")
    actual = g.get_repo_contents('_posts')
    assert expected == actual

def test_GitHub_parse_by_key():
    g = GitHub('', '')
    expected = ['data-pull', 'data-push']
    data = [{"name":"data-push"},{"name":"data-pull"},{"name":"nondata-push"}]
    actual = g.parse_by_key(data, 'name', 'data')
    assert expected.sort() == actual.sort()
