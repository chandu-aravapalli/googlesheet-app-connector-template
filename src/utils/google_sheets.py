import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google_auth_httplib2

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]
SERVICE_ACCOUNT_FILE = "/usr/src/app/quail-asset-7c70b02f0362.json"

def get_service_account_info():
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f)
    else:
        raise ValueError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

def get_google_sheets_service(readonly=False):
    service_account_info = get_service_account_info()
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly'] if readonly else ['https://www.googleapis.com/auth/spreadsheets']
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=scopes)
    http = google_auth_httplib2.AuthorizedHttp(credentials)
    return build('sheets', 'v4', http=http, cache_discovery=False) 