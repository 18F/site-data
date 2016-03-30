import os
import json
from apiclient.http import HttpRequest
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

def get_service(scope, key_file_location, service_account_email):
    """Get a service that communicates to Google's API
    args:
        scope: a list of auth scopes to authorize for the application
        key_file_location: The path to a valid service account file
        service_account_email: the service account email address

    returns:
        a service that is connected to the specified API
    """
    with open(key_file_location) as data_file:
        key = json.load(data_file)
    credentials = ServiceAccountCredentials.from_json_keyfile_name( key_file_location, scope )
    http = credentials.authorize(httplib2.Http())

    # Build the object
    service = build('analytics', 'v3', http=http)
    return service

def get_first_profile_id(service):
    # Use an analytics service object to get the first profile id

    accounts = service.management().accounts().list().execute()

    if accounts.get('items'):
        # Get the first account
        account = accounts.get('items')[0].get('id')

        # Get a list of all views for the first property
        properties = service.management().webproperties().list(accountId=account).execute()

        if properties.get('items'):
            property = properties.get('items')[0].get('id')

            #get a list of all views (profiles) for the first property
            profiles = service.management().profiles().list(
            accountId=account,
            webPropertyId=property).execute()

        if profiles.get('items'):
            return profiles.get('items')[0].get('id')

    return None

def get_sessions(service, profile_id):
    # Use the analytics service to query the reporting API
    # for the number of sessions within the past 30 days.
    return service.data().ga().get(
        ids='ga:%s' % profile_id,
        start_date='30daysAgo',
        end_date='yesterday',
        metrics='ga:sessions').execute()

def get_sessions_by_month(service, profile_id, start, end):
    # Use the analytics service to query the reporting API
    # for the number of sessions within each month between start and end
    results = service.data().ga().get(
        ids="ga:{0}".format(profile_id),
        start_date=start,
        end_date=end,
        metrics='ga:sessions'
    ).execute()
    # {'end-date': '2016-03-30', 'max-results': 1000, 'start-date': '2016-03-30', 'ids': 'ga:82926493', 'start-index': 1, 'metrics': ['ga:sessions']}
    # 'totalsForAllResults': {'ga:sessions': '1487'}
    return results['totalsForAllResults']['ga:sessions']

def print_results(results):
    if results:
        name = results.get('profileInfo').get('profileName')
        print('View (Profile): {0}'.format(name))
        print('Total Sessions: {0}'.format(results.get('rows')[0][0]))
    else:
        print('No results')

def main():
    # Define the scopes
    scope = ['https://www.googleapis.com/auth/analytics.readonly']
    service_account_email = "blogalytics@api-project-157870762122.gsa.gov.iam.gserviceaccount.com"
    key_file_location = "{0}/_data/secrets.json".format(os.getcwd())

    # auth and construct
    service = get_service(scope, key_file_location, service_account_email)
    profile = get_first_profile_id(service)
    # print_results(get_sessions(service, profile))
    return [service, profile]

if __name__ == '__main__':
    main()
