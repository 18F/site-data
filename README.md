# site-data: The 18F Site Manager
[![Build
Status](https://travis-ci.org/18F/site-data.svg?branch=master)](https://travis-ci.org/18F/site-data)

The 18F Site Manager is a resource the 18F Outreach team uses to manage different aspects of the 18F website and blog. It was originally created to help track the growth in authorship from month to month but has recently grown to include a status report of sorts on blog posts as they move through the approval process.

The project is currently hosted at https://blogalytics.18f.gov and is password-protected. Ask someone on the outreach team for the user name and password if you'd like access.

This is very much a work in progress. Ideally the near term future of this project will give the team insight into how long it takes each post to go through the publishing process from idea to published. The longer term would also allow us to visualize the posts that are in each stage and interface with the GitHub API to move posts from one phase to the next as they are ready.

## Getting started

First, request write access to the repository from a current member of the team. Then, generate a new API token by following the directions on github [here](https://help.github.com/articles/creating-an-access-token-for-command-line-use/).

## Installing

After you've cloned this repo and made a Virtualenv with Python 2.x ([soon to be 3.x](https://github.com/18F/site-data/issues/2)), run:

    pip install -r requirements.txt

## Configuring

You'll need to make your own local .env file and populate it with your GitHub username and authentication info.

    cp .env-example .env

Unless you're using a tool like [autoenv](https://github.com/kennethreitz/autoenv), you'll need to `source .env`
before running.

Then create the `site-data-dev` database:

    createdb site-data-dev

and set it up

    python manage.py db upgrade

## Running

Run the server like so:

    honcho start

Then you should be able to access the app at `http://localhost:5000`.

### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
