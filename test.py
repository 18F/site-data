from lib.git_parse import GitHub, drafts_api, GH_DATE_FORMAT
import os, nose, json, requests, requests_mock, datetime
from nose.tools import with_setup
from nose.plugins.skip import Skip, SkipTest
from app.app import app

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
    assert actual == [{'name': '18f.gsa.gov'}]

@requests_mock.mock()
def test_GitHub_fetch_issues(m):
    g= GitHub('18f.gsa.gov', '18F')
    url = "%s/repos/%s/%s/issues?per_page=100" % (g.api, g.owner, g.repo)
    expected = [{"number": i} for i in range(100)]
    m.get(url, content=json.dumps(expected), status_code=200, headers={'Content-Type': 'application/json'})
    actual = g.fetch_issues()
    assert actual == expected

@requests_mock.mock()
def test_GitHub_fetch_issues_request_not_ok(m):
    g= GitHub('18f.gsa.gov', '18F')
    url = "%s/repos/%s/%s/issues" % (g.api, g.owner, g.repo)
    m.get(url, text="I'm a teapot", status_code=418)
    actual = g.fetch_issues()
    assert actual == False

def test_GitHub_split_by_event():
    events = list()
    expected = list()
    events.append({'event': 'milestoned', 'name': 'Issue 0'})
    events.append({'event': 'closed', 'name': 'Issue 1'})
    expected.append(events[0])
    g = GitHub('18f.gsa.gov', '18F')
    actual = g.split_by_event(events, 'milestoned')
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

def _issues(start=datetime.datetime(2015, 1, 1), n_issues = 100, offset=0):
    return [{
        'number': i,
        'updated_at': (start + datetime.timedelta(days=i)).strftime(GH_DATE_FORMAT)
    } for i in range(offset, offset + n_issues)]

@requests_mock.mock()
def test_GitHub_fetch_issues(m):
    expected = json.dumps(_issues())
    m.get(drafts_api.git_url('issues'), content=expected, status_code=200,
          headers={'Content-Type': 'application/json'})
    actual = drafts_api.fetch_issues()
    assert json.loads(expected) == actual

@requests_mock.mock()
def test_GitHub_fetch_assembles_multiple_pages(m):

    def _register_get(since, content):
        url = '{0}?sort=updated&per_page=10&direction=asc&since={1}'.format(
            drafts_api.git_url('issues'),
            since
        )
        app.logger.info('registering mock for {0}'.format(url))
        m.get(url, content=content, complete_qs=False,
            status_code=200, headers={'Content-Type': 'application/json'})

    expected = []
    last_since = datetime.datetime(2015, 1, 1).strftime(GH_DATE_FORMAT)
    for offset in (0, 10, 20):
        issue_group = _issues(n_issues=10, offset=offset)
        _register_get(last_since, json.dumps(issue_group))
        expected.extend(issue_group)
        last_since = issue_group[-1]['updated_at']
    _register_get(last_since, json.dumps([]))

    actual = drafts_api.fetch_issues(since=expected[0]['updated_at'],
        per_page=10)
    assert expected == actual
