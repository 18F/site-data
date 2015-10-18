"""A simple example of how to access the Google Analytics API."""

import argparse

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools
import json



def get_service(api_name, api_version, scope, key_file_location,
                service_account_email):
  """Get a service that communicates to a Google API.

  Args:
    api_name: The name of the api to connect to.
    api_version: The api version to connect to.
    scope: A list auth scopes to authorize for the application.
    key_file_location: The path to a valid service account p12 key file.
    service_account_email: The service account email address.

  Returns:
    A service that is connected to the specified API.
  """

  f = open(key_file_location, 'rb')
  key = f.read()
  f.close()

  credentials = SignedJwtAssertionCredentials(service_account_email, key,
    scope=scope)

  http = credentials.authorize(httplib2.Http())

  # Build the service object.
  service = build(api_name, api_version, http=http)

  return service


def get_first_profile_id(service):
  # Use the Analytics service object to get the first profile id.

  # Get a list of all Google Analytics accounts for this user
  accounts = service.management().accounts().list().execute()

  if accounts.get('items'):
    # Get the first Google Analytics account.
    account = accounts.get('items')[0].get('id')

    # Get a list of all the properties for the first account.
    properties = service.management().webproperties().list(
        accountId=account).execute()

    if properties.get('items'):
      # Get the first property id.
      property = properties.get('items')[0].get('id')

      # Get a list of all views (profiles) for the first property.
      profiles = service.management().profiles().list(
          accountId=account,
          webPropertyId=property).execute()

      if profiles.get('items'):
        # return the first view (profile) id.
        return profiles.get('items')[0].get('id')

  return None


def get_30day_results(service, profile_id):
  return service.data().ga().get(
      ids='ga:95661594',
      start_date='30daysAgo',
      end_date='today',
      metrics='ga:pageviews',
      dimensions='ga:pagePath',
      sort='-ga:pageviews',
      max_results='10').execute()

def get_7day_results(service, profile_id):
  return service.data().ga().get(
      ids='ga:95661594',
      start_date='7daysAgo',
      end_date='today',
      metrics='ga:pageviews',
      dimensions='ga:pagePath',
      sort='-ga:pageviews',
      max_results='10').execute()

def get_1day_results(service, profile_id):
  return service.data().ga().get(
      ids='ga:95661594',
      start_date='yesterday',
      end_date='today',
      metrics='ga:pageviews',
      dimensions='ga:pagePath',
      sort='-ga:pageviews',
      max_results='10').execute()

def main():
  # Define the auth scopes to request.
  scope = ['https://www.googleapis.com/auth/analytics.readonly']

  # Use the developer console and replace the values with your
  # service account email and relative location of your key file.
  service_account_email = '170342286960-tnumthpb63e6sbj310j7n29b3mbhio0u@developer.gserviceaccount.com'
  key_file_location = 'tony-ga-auth.p12'

  # Authenticate and construct service.
  service = get_service('analytics', 'v3', scope, key_file_location,
    service_account_email)
  profile = get_first_profile_id(service)

  json.dump(get_30day_results(service, profile), open('../app/static/results_30day.json', 'w'))
  json.dump(get_7day_results(service, profile), open('../app/static/results_7day.json', 'w'))
  json.dump(get_1day_results(service, profile), open('../app/static/results_1day.json', 'w'))

if __name__ == '__main__':
  main()
