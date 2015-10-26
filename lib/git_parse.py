import os, requests, yaml
import yaml
from requests.auth import HTTPBasicAuth
from datetime import datetime

GH_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
BEGINNING_OF_TIME = '1970-01-01T00:00:00Z'


class GitHub():
    def __init__(self, repo, owner, branch='master'):
        """Sets up the class
        ## Parameters:
        *   repo, str, the repo we want to work with (usually necessary for all
            but a reqired parameter for now).
        *   owner, str, the owner of repo this usually is necessary
        *   branch, str, branch of the repo to target

        >>> gh = GitHub('18f.gsa.gov', '18F', 'staging')

        This will set up an instance of this class with repo and owner set to
        18F and targeting the 'staging' branch of the '18f.gsa.gov' repo.

        Once you have `gh` set you can call methods like `gh.fetch_endpoint()`
        Examples thorughout this documentation will use `gh` this way."""
        self.repo = repo.strip()
        self.owner = owner.strip()
        self.branch = branch
        self.api = "https://api.github.com"
        self.raw = "https://raw.githubusercontent.com"
        self.user = os.environ['GITHUB_USER']
        self.auth = os.environ['GITHUB_AUTH']

    def fetch_raw(self, request_string):
        """Gets the raw contents of a file from a raw.githubusercontent URL
        allowing you to fetch a file from a specific HEAD or SHA.

        Appends https://raw.githubusercontent.com/ to a passed URL string

        Example:
        >>> gh = GitHub("", "")
        >>> gh.fetch_raw("18F/18f.gsa.gov/staging/Gemfile.lock")

        This will get the Gemfile lock from GitHub as it exists at the current
        HEAD of the staging branch. This is similar to but a bit simpler
        implementation of making a request to the contents endpoint of the API.

        Returns the content if the request returns 200/OK or False."""
        url = "%s/%s" % (self.raw, request_string)
        content = requests.get(url)
        if content.ok:
            return content
        else:
            return False

    def raw_file(self, path, branch='staging'):
        "Gets raw file content (at STAGING) from github, given file path."
        request_string = '{owner}/{repo}/{branch}/{path}'.format(path=path,
                                                               ** self.__dict__)
        return self.fetch_raw(request_string)

    def yaml(self, path, segment_number):
        """Returns data from Jekyll/YAML file.

        Splits the file content on ---, then YAML-parses and returns the
        `segment_number`th element from the split."""
        raw = self.raw_file(path)
        if raw:
            segments = raw.text.split('---')
            return yaml.load(segments[segment_number])
        else:
            return {}

    def git_url(self, endpoint):
        return "%s/repos/%s/%s/%s" % (self.api, self.owner, self.repo,
                                      endpoint)

    def fetch_endpoint(self, endpoint, params={}):
        """Fetches any endpoint off of the repositories API.
        `self.owner` and `self.repo` are passed as parameters to `__init__`.
        `self.api` is set by default but could be overridden (if you're
        pointing at a GitHub Enterprise instance, for example).
        Parameters:
        endpoint, str,
        Like most methods in this class, the request is automatically
        authenticated based on environment variables GITHUB_USER and
        GITHUB_AUTH.
        >>> gh = GitHub("18f.gsa.gov", "18F")
        >>> gh.fetch_endpoint('')
        This will fetch all the data about 18F/18f.gsa.gov (see __init__)
        Example: gh.fetch_endpoint('issues?per_page=100')
        This will fetch the 100 most recent issues on gh.owner/gh.repo"""
        content = requests.get(self.git_url(endpoint),
                               params=params,
                               auth=HTTPBasicAuth(self.user, self.auth))
        if (content.ok):
            return content
        else:
            return False

    def fetch_commits(self, params={}):
        commits = self.fetch_endpoint('commits', params=params)
        if commits:
            return commits.json()
        else:
            return False

    def fetch_issues(self, since=BEGINNING_OF_TIME, **params):
        try:
            params['since'] = since.strftime(GH_DATE_FORMAT)
        except AttributeError:
            params['since'] = since  # did not need str conversion
        params['per_page'] = params.get('per_page', 100)
        params['sort'] = 'updated'
        params['direction'] = 'asc'
        issues = self.fetch_endpoint('issues', params=params)
        if not issues:
            return False
        result = {}
        new_issues = [i for i in issues.json() if i['number'] not in result]
        while new_issues:
            result.update({i['number']: i for i in new_issues})
            # Github seems to be ignoring `sort` parameter, have to
            # check all results, alas
            params['since'] = _latest_update(new_issues)
            issues = self.fetch_endpoint('issues', params=params)
            new_issues = [i for i in issues.json() if i['number'] not in result
                          ]
        return result.values()

    def split_by_event(self, events, part):
        reduced = list()
        for e in events:
            if e['event'] == part:
                reduced.append(e)
        return reduced

    def fetch_issue_events(self, issue, part=None, name=None):
        events = self.fetch_endpoint('issues/%s/events?per_page=100' % issue)
        if events:
            if part != None:
                requested = self.split_by_event(events.json(), part)
            else:
                requested = events.json()
            return requested
        else:
            return False

    def fetch_milestone(self, issue):
        return self.fetch_issue_events(issue, 'milestoned')

    def file_at_commit(self, sha, filename):
        url = "%s/%s/%s/%s" % (self.owner, self.repo, sha, filename)
        contents = self.fetch_raw(url)
        return (contents and contents.content) or ''

    def parse_by_key(self, data, key, match):
        i = 0
        matches = list()
        while i < len(data):
            if data[i].get(key).startswith(match):
                matches.append(data[i].get(key))
            i = i + 1
        return matches


site_api = GitHub('18f.gsa.gov', '18F', branch='staging')
drafts_api = GitHub('blog-drafts', '18F', branch='staging')
hub_api = GitHub('hub', '18F', branch='master')


def _latest_update(items, field_name='updated_at'):
    "Returns latest `field_name` in `items`"
    updates = [datetime.strptime(i.get(field_name, BEGINNING_OF_TIME),
                                 GH_DATE_FORMAT) for i in items]
    return max(updates).strftime(GH_DATE_FORMAT)
