import calendar
from datetime import date, datetime
from functools import total_ordering
from math import pi

from sqlalchemy import func

from lib.git_parse import (drafts_api, hub_api, private_18f_data_repo,
                           site_api, site_repo)
from lib.utils import to_py_date

from . import db

author_months = db.Table(
    'author_months',
    db.Column('month_begin', db.Date(), db.ForeignKey('month.begin')),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id')))


@total_ordering
class Month(db.Model):
    begin = db.Column(db.Date(), primary_key=True)
    authors = db.relationship('Author',
                              secondary=author_months,
                              backref=db.backref('months',
                                                 lazy='dynamic'),
                              collection_class=set)

    def __str__(self):
        return '{0}-{1}'.format(self.begin.year, self.begin.month)

    @classmethod
    def non_empty(cls):
        return cls.query.filter(cls.authors)

    @classmethod
    def author_count_by_location(cls, location, is_published=True):
        """Returns list of (month name, # of authors) tuples"""
        return [(
            str(m),
            len([a
                 for a in m.authors
                 if a.is_in(location) and a.is_published() == is_published]))
                for m in cls.non_empty()]

    @classmethod
    def get_or_create(cls, first_day):
        return cls.query.get(first_day) or cls(begin=first_day)

    def next(self):
        if self.begin.month == 12:
            next_begin = date(self.begin.year + 1, 1, 1)
        else:
            next_begin = date(self.begin.year, self.begin.month + 1, 1)
        return self.get_or_create(next_begin)

    def end(self):
        last_day = calendar.monthrange(self.begin.year, self.begin.month)[1]
        return date(self.begin.year, self.begin.month, last_day)

    @classmethod
    def create_missing(cls):
        "Populate DB with all months up to today, including their authors."
        FIRST_MONTH_OF_BLOG = date(2014, 3, 1)
        month = cls.get_or_create(FIRST_MONTH_OF_BLOG)
        while month.begin <= date.today():
            db.session.add(month)
            month = month.next()
        db.session.commit()

    def __eq__(self, other):
        return self.begin == other.begin

    def __gt__(self, other):
        return self.begin > other.begin

    # other comparison operators automagically inferred by `total_ordering`

    def _date_range(self):
        month_begin = "{0}-01".format(self)
        month_end = "{0}-{1}".format(self, self.end().day)
        return {"since": month_begin, "until": month_end}


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    authors = db.relationship('Author',
                              cascade='all, delete-orphan',
                              backref='team')


class DutyStation(db.Model):
    airport_code = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timezone = db.Column(db.Text, nullable=False)
    authors = db.relationship('Author',
                              collection_class=set,
                              backref='duty_station')

    @classmethod
    def fetch(cls):
        data = hub_api.yaml('_data/locations.yml', 1)
        for d in data:
            if not cls.query.get(d['code']):
                d['airport_code'] = d.pop('code')
                d['name'] = d.pop('label')
                db.session.add(cls(**d))
        db.session.commit()

    def __str__(self):
        return self.airport_code

    _groups = {'DCA': 'DC', 'SFO': 'SF'}

    @property
    def group(self):
        return self._groups.get(self.airport_code, 'OTHER')


post_authors = db.Table('post_authors',
                        db.Column('post_id',
                                  db.Integer,
                                  db.ForeignKey('post.id'),
                                  primary_key=True),
                        db.Column('author_id',
                                  db.Integer,
                                  db.ForeignKey('author.id'),
                                  primary_key=True), )


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False, unique=True, index=True)
    download_url = db.Column(db.Text, nullable=False, unique=True)
    post_date = db.Column(db.Date(), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    tumblr_url = db.Column(db.Text)
    authors = db.relationship('Author',
                              secondary=post_authors,
                              backref=db.backref('posts',
                                                 lazy='dynamic'),
                              collection_class=set)

    @classmethod
    def fetch(cls):
        for (url, download_url, post_date) in site_repo.urls():
            if not cls.query.filter_by(url=url).first():
                frontmatter = site_repo.frontmatter(download_url)
                post = cls(url=url,
                           download_url=download_url,
                           post_date=post_date,
                           title=frontmatter.get('title'),
                           description=frontmatter.get('description'),
                           tumblr_url=frontmatter.get('tumblr_url'), )
                for author_username in frontmatter.get('authors'):
                    author = Author.query.filter(func.lower(
                        Author.username) == author_username.lower()).first()
                    if author:
                        post.authors.add(author)
                db.session.add(post)
        GithubQueryLog.log('posts')
        db.session.commit()


labels_issues = db.Table(
    'labels_issues',
    db.Column('label_id', db.Integer, db.ForeignKey('label.id')),
    db.Column('issue_id', db.Integer, db.ForeignKey('issue.id')))


class ClosedMilestone(object):
    "Milestone-like standin indicating an issue's closure"

    title = 'closed'
    state = True
    commit_id = None
    color = 'grey'
    opacity = 0.4
    is_terminal = True
    arclength = 2 * pi

    def __init__(self, issue):
        self.created_at = issue.closed_at
        self.url = issue.html_url
        self.issue = issue


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    title = db.Column(db.String())
    body = db.Column(db.String())
    state = db.Column(db.String())
    creator_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    assignee_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    comments = db.Column(db.String())
    locked = db.Column(db.Boolean)
    url = db.Column(db.String(), nullable=True)
    events_url = db.Column(db.String(), nullable=True)
    labels_url = db.Column(db.String(), nullable=True)
    comments_url = db.Column(db.String(), nullable=True)
    html_url = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.Date(), default=date.today)
    updated_at = db.Column(db.Date(), default=date.today)
    closed_at = db.Column(db.Date(), nullable=True)
    labels = db.relationship('Label',
                             secondary=labels_issues,
                             backref=db.backref('issues',
                                                lazy='dynamic'))
    milestones = db.relationship('Milestone',
                                 cascade='all, delete-orphan',
                                 order_by='Milestone.created_at',
                                 backref='issue')
    events = db.relationship('Event', cascade='all, delete-orphan')

    @classmethod
    def from_gh_data(cls, issue_data):
        """Given dict of issue data fetched from GitHub API, return instance.

        If the issue already exists, delete it (and its milestones)
        and replace it."""
        issue = cls.query.filter_by(number=issue_data.get('number')).first()
        if issue:
            db.session.delete(issue)
        db.session.commit()
        author = Author.query.filter_by(
            github=issue_data['user'].get('login')).first()
        if issue_data.get('assignee'):
            assignee = Author.query.filter_by(
                github=issue_data['assignee'].get('login')).first()
        else:
            assignee = None
        insertable = {
            'id': issue_data.get('id'),
            'number': issue_data.get('number'),
            'title': issue_data.get('title'),
            'state': issue_data.get('state'),
            'author': author,
            'assignee': assignee,
            'body': issue_data.get('body'),
            'locked': issue_data.get('locked'),
            'url': issue_data.get('url'),
            'labels_url': issue_data.get('labels_url'),
            'html_url': issue_data.get('html_url'),
            'events_url': issue_data.get('events_url'),
            'updated_at': to_py_date(issue_data['updated_at']),
            'created_at': to_py_date(issue_data['created_at']),
            'closed_at': to_py_date(issue_data['closed_at']),
        }
        issue = cls(**insertable)
        for label_data in issue_data['labels']:
            issue.labels.append(Label.get_or_create(label_data))
        db.session.add(issue)
        db.session.commit()
        return issue

    def virtual_closure_milestone(self):
        "Impersonate a Milestone represeting this issue's closure."
        return {'title': 'closed',
                'state': True,
                'commit_id': None,
                'created_at': self.closed_at,
                'url': self.html_url,
                'color': 'grey',
                'opacity': 0.4,
                'is_terminal': True,
                'issue': self,
                'arclength': 2 * pi}

    def milestones_for_chart(self):
        "Appends a virtual `closed` milestone, if needed, to those in the DB"
        for m in self.milestones:
            yield m
        if self.closed_at and 'posted' not in [m.title
                                               for m in self.milestones]:
            yield ClosedMilestone(self)

    @classmethod
    def fetch(cls, since):
        issues = drafts_api.fetch_issues(since=since)
        for issue_data in issues:
            issue = cls.from_gh_data(issue_data)
            milestones = drafts_api.fetch_milestone(issue.number)
            for milestone_data in milestones:
                issue.milestones.append(Milestone.from_gh_data(milestone_data))
            events = drafts_api.fetch_issue_events(issue.number)
            for event_data in events:
                issue.events.append(Event.from_gh_data(event_data))
        GithubQueryLog.log('issues')
        db.session.commit()

    _history_summary_template = "{} -- {}"

    def history_summary(self):
        "Text summary of an issue's history of milestones"
        result = [self._history_summary_template.format(
            self.created_at.strftime('%b %d'), 'created')]
        for m in self.milestones:
            result.append(self._history_summary_template.format(
                m.created_at.strftime('%b %d'), m.title))
        return "<br />\n".join(result)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String())  # in 18F site
    github = db.Column(db.String())
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    full_name = db.Column(db.String())
    url = db.Column(db.String(), nullable=True)
    pronouns = db.Column(db.String(), nullable=True)
    first_post = db.Column(db.Date(), nullable=True)
    airport_code = db.Column(db.String(),
                             db.ForeignKey('duty_station.airport_code'))
    team_id = db.Column(db.Integer(), db.ForeignKey('team.id'))
    created = db.relationship('Issue',
                              foreign_keys=[Issue.creator_id, ],
                              backref='author')
    assigned = db.relationship('Issue',
                               foreign_keys=[Issue.assignee_id, ],
                               backref='assignee')
    _scalar_fields = ['github', 'first_name', 'last_name', 'full_name', 'url',
                      'pronouns', 'airport_code']

    def is_in(self, location):
        return self.duty_station and self.duty_station.group == location

    def is_published(self):
        return self.posts.count() > 0

    def record_post_history(self):
        if self.posts.first():
            self.first_post = min(p.post_date for p in self.posts)
            first_month = self.first_post.replace(day=1)
            for m in Month.query.filter(Month.begin >= first_month):
                if m not in self.months:
                    self.months.append(m)
        else:
            self.first_post = None

    def lookup_team(self):
        "Query 18F website for an author's team in 18F"
        data = site_api.yaml('_team/{0}.md'.format(self.username), 1)
        team_name = data.get('team')
        if team_name:
            team = Team.query.filter_by(name=team_name).first() or Team(
                name=team_name)
            db.session.add(team)
            self.team = team

    @classmethod
    def fetch(cls):
        "Create an Author for everyone in private-data repo"
        for member in private_18f_data_repo.team_members():
            author = cls.query.filter_by(username=member['name']).first()
            if author:
                for field_name in cls._scalar_fields:
                    if field_name in member:
                        setattr(author, field_name, member[field_name])
            else:
                dct = {fn: member[fn]
                       for fn in cls._scalar_fields if fn in member}
                dct['username'] = member['name']
                author = cls(**dct)
                db.session.add(author)
            if 'location' in member:
                author.duty_station = DutyStation.query.filter_by(
                    airport_code=member['location']).first()
            author.lookup_team()
        GithubQueryLog.log('authors')
        db.session.commit()

    _authorship_histogram_qry = """
        WITH postcount AS (
          SELECT a.username,
                 COUNT(pa) AS n
          FROM   author a
          LEFT OUTER JOIN
                 post_authors pa ON (pa.author_id = a.id)
          GROUP BY a.username)
        SELECT count(*) FILTER (WHERE n = 0) AS n_0,
               count(*) FILTER (WHERE n = 1) AS n_1,
               count(*) FILTER (WHERE n = 2) AS n_2,
               count(*) FILTER (WHERE n BETWEEN 3 AND 5) AS n_3_to_5,
               count(*) FILTER (WHERE n BETWEEN 6 AND 10) AS n_6_to_10,
               count(*) FILTER (WHERE n > 10) AS n_11_plus
        FROM postcount;
        """

    @classmethod
    def authorship_histogram(cls):
        return db.engine.execute(cls._authorship_histogram_qry).fetchone()

    _authorship_histogram_by_team_qry = """
    WITH team_count AS (
        WITH team_summary AS (
        WITH team_count AS (
            SELECT t.id,
                t.name,
                COUNT(a.*) AS n
            FROM   team t
            JOIN   author a ON (a.team_id = t.id)
            GROUP BY t.id, t.name
        )
        SELECT id,
                CASE WHEN n < 1 THEN 'Other'  -- increase this to report small teams together
                    ELSE name END AS name,
                n
        FROM team_count
        ),
        postcount AS (
            SELECT a.full_name,
                   a.last_name,
                   a.username,
                   a.team_id,
                   COUNT(pa) AS n
            FROM   author a
            LEFT OUTER JOIN
                    post_authors pa ON (pa.author_id = a.id)
            GROUP BY a.full_name, a.last_name, a.username, a.team_id)
        SELECT ts.name,
            pc.username,
            pc.full_name,
            pc.last_name,
            pc.n
        FROM   team_summary ts
        JOIN   postcount pc ON (ts.id = pc.team_id)
    )
    SELECT  name AS __department,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 0) AS n_0,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 1) AS n_1,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 2) AS n_2,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n BETWEEN 3 AND 5) AS n_3_to_5,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n BETWEEN 6 AND 10) AS n_6_to_10,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n > 10) AS n_11_plus
    FROM team_count
    GROUP BY name
    """

    @classmethod
    def authorship_histogram_by_team(cls):
        return list(db.engine.execute(cls._authorship_histogram_by_team_qry))

    _authorship_histogram_by_loc_qry = """
    WITH loc_count AS (
        WITH loc_summary AS (
        WITH loc_count AS (
            SELECT ds.airport_code,
                   ds.name,
                   COUNT(a.*) AS n
            FROM   duty_station ds
            JOIN   author a ON (a.airport_code = ds.airport_code)
            GROUP BY ds.airport_code, ds.name
        )
        SELECT airport_code,
               CASE WHEN n < 3 THEN 'Other'
                    ELSE name END AS name,
               n
        FROM loc_count
        ),
        postcount AS (
            SELECT a.full_name,
                   a.last_name,
                   a.username,
                   a.airport_code,
                   COUNT(pa) AS n
            FROM   author a
            LEFT OUTER JOIN
                    post_authors pa ON (pa.author_id = a.id)
            GROUP BY a.full_name, a.last_name, a.username, a.airport_code)
        SELECT ls.name,
            pc.username,
            pc.full_name,
            pc.last_name,
            pc.n
        FROM   loc_summary ls
        JOIN   postcount pc ON (ls.airport_code = pc.airport_code)
    )
    SELECT  name AS __location,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 0) AS n_0,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 1) AS n_1,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n = 2) AS n_2,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n BETWEEN 3 AND 5) AS n_3_to_5,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n BETWEEN 6 AND 10) AS n_6_to_10,
            array_agg(full_name ORDER BY last_name) FILTER (WHERE n > 10) AS n_11_plus
    FROM loc_count
    GROUP BY name
    """

    @classmethod
    def authorship_histogram_by_loc(cls):
        return list(db.engine.execute(cls._authorship_histogram_by_loc_qry))


class GithubQueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_type = db.Column(db.String(), unique=True, nullable=False)
    queried_at = db.Column(db.DateTime(), default=datetime.now)

    @classmethod
    def last_query_datetime(cls, query_type):
        qlog = cls.query.filter_by(query_type=query_type).first()
        if qlog:
            return qlog.queried_at
        else:
            return datetime.fromtimestamp(0)

    @classmethod
    def log(cls, query_type):
        qlog = cls.query.filter_by(query_type=query_type).first()
        if qlog:
            qlog.queried_at = datetime.now()
        else:
            qlog = cls(query_type=query_type, queried_at=datetime.now())
        db.session.add(qlog)


class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    url = db.Column(db.String())
    color = db.Column(db.String(), nullable=True)

    @classmethod
    def get_or_create(cls, label_data):
        label = cls.query.filter_by(name=label_data['name']).first() \
                or cls(**label_data)
        return label


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.String())
    url = db.Column(db.String())
    actor = db.Column(db.String())
    event = db.Column(db.String())
    created_at = db.Column(db.Date())
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

    @classmethod
    def from_gh_data(cls, event_data):
        "Given dict of event data fetched from GitHub API, return instance"
        return cls(id=event_data['id'],
                   commit_id=event_data['commit_id'],
                   url=event_data['url'],
                   actor=event_data['actor'].get('login') if event_data[
                       'actor'] else None,
                   event=event_data['event'],
                   created_at=to_py_date(event_data.get('created_at')), )


class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    state = db.Column(db.Boolean, nullable=False)
    commit_id = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.Date(), default=date.today)
    url = db.Column(db.String())
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

    @classmethod
    def from_gh_data(cls, milestone_data):

        "Given dict of milestone data fetched from GitHub API, return instance"
        return cls(id=milestone_data['id'],
                   title=milestone_data['milestone']['title'],
                   state=(milestone_data['event'] == 'milestoned'),
                   commit_id=milestone_data.get('commit_id'),
                   created_at=to_py_date(milestone_data.get('created_at')),
                   url=milestone_data.get('url'), )

    _statuses = {'idea': 0,
                 'draft': 1,
                 'to edit': 2,
                 'ready': 3,
                 'ready to approve': 3,
                 'approved': 4,
                 'posted': 5, }
    _colors = ('cyan',
               'blue',
               'yellow',
               'orange',
               'green',
               'purple', )  # TODO: 508 these?
    _opacities = (0.2, 0.4, 0.6, 0.7, 0.8, 0.9)
    _arclength_per_step = (2 * pi) / (len(_colors) + 1)

    @property
    def arclength(self):
        "This milestone, represented as a clock-style arc toward completion"
        idx = self._statuses[self.title]
        return self._arclength_per_step * (idx + 1)

    @property
    def color(self):
        "Color representing this milestone's degree of completion"
        idx = self._statuses[self.title]
        return self._colors[idx]

    @property
    def opacity(self):
        "Opacity representing this milestone's degree of completion"
        idx = self._statuses[self.title]
        return self._opacities[idx]

    @property
    def is_terminal(self):
        "A final milestone, no further milestones expected for this issue"
        idx = self._statuses[self.title]
        return idx == len(self._colors) - 1

    def next(self):
        "The `state`==`True` milestone following this one in this Issue"
        active_milestones = [m
                             for m in self.issue.milestones_for_chart()
                             if m.state]
        idx = active_milestones.index(self)
        try:
            return active_milestones[idx + 1]
        except IndexError:
            return None


def update_db_from_github(refresh_timedelta):
    """Refresh author and issue data from Github / 18f API.

    Args:
        refresh_timedelta: Pull from each data source only if the last pull
            was at least this long ago.
    """

    Month.create_missing()
    last_query = GithubQueryLog.last_query_datetime('authors')
    if (datetime.now() - last_query) > refresh_timedelta:
        DutyStation.fetch()
        Author.fetch()
    last_query = GithubQueryLog.last_query_datetime('posts')
    if (datetime.now() - last_query) > refresh_timedelta:
        Post.fetch()
        for author in Author.query:
            author.record_post_history()
    last_query = GithubQueryLog.last_query_datetime('issues')
    if (datetime.now() - last_query) > refresh_timedelta:
        Issue.fetch(since=last_query)
