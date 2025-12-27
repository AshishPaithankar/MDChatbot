from django.conf import settings
#from decouple import config
from datetime import timedelta

# in original project we have imported the days from .env file do we have to do it here also ?
class JWTConfigurations:
    ACCESS_TOKEN_LIFETIME = timedelta(days=365)
    REFRESH_TOKEN_LIFETIME = timedelta(days=365)
    SIGNING_KEY = settings.SECRET_KEY
    ALGORITHM = "HS256"



