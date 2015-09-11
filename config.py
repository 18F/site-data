import os
# set PORT to the port you want the site served from, for cloud foundry
# deployment you probably have VCAP_APP_PORT set in the production environment
if os.environ.has_key('VCAP_APP_PORT'):
    PORT = int(os.getenv("VCAP_APP_PORT"))
else:
    PORT = 5000

# Set environment variables for the urls of your production and staging servers
SERVERS = {"production":os.environ['PROD'], "staging":os.environ['STAGING']}
ENV = 'local'

# Set your secret key in an environment variable
if os.environ.has_key('SECRET'):
    SECRET_KEY = os.environ['SECRET']

# change to http if you don't have SSL. tsk tsk
PREFERRED_URL_SCHEME = 'https'
