from collections import OrderedDict

import pygal

from .models import (Author, Event, GithubQueryLog, Issue, Milestone, Month,
                     Team, db)

WIDTH = 800
HEIGHT = 400

chart_style = dict(explicit_size=True,
                   style=pygal.style.DarkGreenBlueStyle,
                   x_label_rotation=70,
                   x_labels_major_every=3,
                   show_minor_x_labels=False, )


def n_authors():
    """PyGal chart of cumulative number of authors per month."""

    author_count = [(str(m), len(m.authors)) for m in Month.non_empty()]
    title = 'Cumulative author count, by month'
    bar_chart = pygal.Bar(title=title, **chart_style)
    bar_chart.x_labels = [ac[0] for ac in author_count]
    bar_chart.add('Author count', [ac[1] for ac in author_count])
    return bar_chart


def n_authors_by_location():
    "PyGal chart of cumulative # of authors per month, by location category."

    title = 'Cumulative author count, by month and location'
    bar_chart = pygal.StackedBar(title=title, **chart_style)
    bar_chart.x_labels = [str(m) for m in Month.non_empty()]
    for loc in ('DC', 'SF', 'OTHER'):
        count = [m[1] for m in Month.author_count_by_location(loc, True)]
        bar_chart.add(loc, count)
    return bar_chart


def n_posts_histogram():

    title = '18F team members by number of posts'
    bar_chart = pygal.StackedBar(title=title,
                                 x_label_rotation=70,
                                 style=pygal.style.DarkGreenBlueStyle, )

    data = Author.authorship_histogram()
    bar_chart.x_labels = [k[2:].replace('_', ' ') for k in data.keys()]
    bar_chart.add('Team members', data.values())
    return bar_chart


def n_authors_by_team():

    title = 'Number of posts per member by team'
    bar_chart = pygal.Bar(title=title,
                          x_label_rotation=70,
                          style=pygal.style.DarkGreenBlueStyle, )

    data = Author.authorship_histogram_by_team()
    for row in data:
        bar = [{'value': len(v or []),
                'label': ', '.join(v or [])} for v in row[1:]]
        bar_chart.add(row[0], bar)
    bar_chart.x_labels = [k[2:].replace('_', ' ') for k in row.keys()[1:]]
    return bar_chart
