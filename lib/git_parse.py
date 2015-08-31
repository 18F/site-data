import os, requests, yaml
from requests.auth import HTTPBasicAuth
class GitHub():
    def __init__(self, repo, owner):
        """Sets up the class
        ## Parameters:
        *   repo, str, the repo we want to work with (usually necessary for all
            but a reqired parameter for now).
        *   owner, str, the owner of repo this usually is necessary

        >>> gh = GitHub('18f.gsa.gov', '18F')

        This will set up an instance of this class with repo and owner set to
        18F and targeting the '18f.gsa.gov' repo.

        Once you have `gh` set you can call methods like `gh.fetch_endpoint()`
        Examples thorughout this documentation will use `gh` this way."""
        self.repo = repo.strip()
        self.owner = owner.strip()
        self.api = "https://api.github.com"
        self.raw = "https://raw.githubusercontent.com"
        self.user = os.environ['GITHUB_USER']
        self.auth = os.environ['GITHUB_AUTH']

    def fetch_raw(self, request_string):
        """Gets the raw contents of a file from a raw.githubusercontent URL

        Appends https://raw.githubusercontent.com/ to a passed URL string
        allowing you to fetch a file from a specific HEAD or SHA.

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

    def fetch_endpoint(self, endpoint):
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
        git_url = "%s/repos/%s/%s/%s" % (self.api, self.owner, self.repo, endpoint)

        content = requests.get(git_url, auth=HTTPBasicAuth(self.user, self.auth))
        if (content.ok):
            return content
        else:
            return False

    def fetch_commits(self, params):
        commits = self.fetch_endpoint('commits')
        if commits:
            return commits.json()
        else:
            return False

    def fetch_issues(self, params=None):
        issues = self.fetch_endpoint('issues?per_page=100')
        if issues:
            return issues.json()
        else:
            return False

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
        return contents.content

    def get_repo_contents(self, path):
        contents = self.fetch_endpoint('contents/%s/' % path)
        return contents.content

    def parse_by_key(self, data, key, match):
        i = 0
        matches = list()
        while i < len(data):
            if data[i].get(key).startswith(match):
                matches.append(data[i].get(key))
            i = i+1
        return matches
