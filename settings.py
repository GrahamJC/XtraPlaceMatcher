import os
import json

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read JSON secrets file
with open(os.path.join(BASE_DIR, 'secrets.json')) as f:
    secrets = json.loads(f.read())

def get_secret(setting):
    try:
        return secrets[setting]
    except KeyError:
        raise ImproperlyConfigured("Secret {0} not found".format(setting))

# OddsMonkey account
OM_USERNAME = get_secret('OM_USERNAME')
OM_PASSWORD = get_secret('OM_PASSWORD')

# ProfitAccumulator account
PA_USERNAME = get_secret('PA_USERNAME')
PA_PASSWORD = get_secret('PA_PASSWORD')
