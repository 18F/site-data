import calendar
from datetime import date, datetime
from functools import total_ordering
from math import pi

from sqlalchemy import func

from lib.git_parse import (drafts_api, hub_api, private_18f_data_repo,
                           site_api, site_repo)
from lib.utils import to_py_date

from . import db
from app.github_issue_lifecycles.app.models import Repo, Issue, Person, Label, Event

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

    @classmethod
    def all_authors(cls):
        for m in cls.non_empty():
            for a in m.authors:
                yield (a, m)


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

    repo = Repo.get_fresh(
        owner_name='18f',
        repo_name='blog-drafts',
        refresh_threshhold_seconds=refresh_timedelta.total_seconds())
    repo.set_milestone_color_map()
