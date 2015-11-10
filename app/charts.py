from .models import GithubQueryLog, Author, Issue, Milestone, Month, Event, db
import pygal

WIDTH = 800
HEIGHT = 400


def n_authors():
    """PyGal chart of cumulative number of authors per month."""

    author_count = [(str(m), len(m.authors)) for m in Month.non_empty()]
    title = 'Cumulative author count, by month'
    bar_chart = pygal.Bar(
        # width=WIDTH, height=HEIGHT,
        explicit_size=True,
        title=title,
        style=pygal.style.DarkGreenBlueStyle)
    bar_chart.x_labels = [ac[0] for ac in author_count]
    bar_chart.add('Author count', [ac[1] for ac in author_count])
    return bar_chart


def n_authors_by_location():
    "PyGal chart of cumulative # of authors per month, by location category."

    title = 'Cumulative author count, by month and location'
    bar_chart = pygal.StackedBar(
        # width=WIDTH, height=HEIGHT,
        explicit_size=True,
        title=title,
        style=pygal.style.DarkGreenBlueStyle)
    bar_chart.x_labels = [str(m) for m in Month.non_empty()]
    for loc in ('DC', 'SF', 'OTHER'):
        bar_chart.add(loc, [m[1] for m in Month.author_count_by_location(loc)])
    return bar_chart
