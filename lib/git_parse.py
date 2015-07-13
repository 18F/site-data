import requests, yaml
"""
parses the first commit from:
git log --before={YYY-MM-DD} --after={YYYY-MM-DD} --pretty=format:"%H"
"""
class GitHub():
  def __init__(self, repo, owner):
    self.repo = repo.strip()
    self.owner = owner.strip()

  def fetch_commits(self, params):
    accept = {
      "since": None,
      "until": None,
      "sha": None,
      "author": None,
      "path": None
    }
    diff = set(params.keys()) - set(accept.keys())
    if diff == set():
      pass
    else:
      for k in diff:
        params.pop(k)

    commits = requests.get("https://api.github.com/repos/%s/%s/commits" % (self.repo, self.owner), params=params)
    if (commits.ok):
      return commits.json()
    else:
      return False

  def file_at_commit(self, sha, filename):
    content = requests.get("https://raw.githubusercontent.com/%s/%s/%s/%s" % (self.repo, self.owner, sha, filename))
    return content.content
