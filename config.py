import os
if os.environ.has_key('VCAP_APP_PORT'):
    PORT = os.environ['VCAP_APP_PORT']
else:
    PORT = 5000

SERVERS = {"production":os.environ['PROD'], "staging":os.environ['STAGING']}
DEBUG = True
