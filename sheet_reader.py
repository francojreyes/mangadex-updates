'''
Reads whitelisted manga ID's and webhooks from google sheets
'''
import re
import os

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# defines
SCOPE = ['https://www.googleapis.com/auth/spreadsheets.readonly',
         'https://www.googleapis.com/auth/drive.readonly']
REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
WEBHOOK_LINK = 'https://discord.com/api/webhooks/'

# read credentials from environment
load_dotenv()
service_account_info = {
    "type": os.getenv('CREDS_TYPE'),
    "project_id": os.getenv('CREDS_PROJECT_ID'),
    "private_key_id": os.getenv('CREDS_PRIVATE_KEY_ID'),
    "private_key": os.getenv('CREDS_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('CREDS_CLIENT_EMAIL'),
    "client_id": os.getenv('CREDS_CLIENT_ID'),
    "auth_uri": os.getenv('CREDS_AUTH_URI'),
    "token_uri": os.getenv('CREDS_TOKEN_URI'),
    "auth_provider_x509_cert_url": os.getenv('CREDS_AUTH_PROVIDER_X509_CERT_URL'),
    "client_x509_cert_url": os.getenv('CREDS_CLIENT_X509_CERT_URL')
}

# add credentials to the account
creds = Credentials.from_service_account_info(
    service_account_info, scopes=SCOPE)

# authorize the clientsheet
client = gspread.authorize(creds)


def get_sheets():
    '''
    Scan all sheets and return the list of webhooks/ids
    Ignores sheets with invalid format
    '''
    sheets = client.openall()

    result = []
    for sheet in sheets:
        sheet_data = {
            'id': sheet.id
        }

        # Get webhooks, filter out invalid links
        try:
            webhooks = sheet.worksheet('webhooks').col_values(1)
            sheet_data['webhooks'] = [w for w in webhooks if WEBHOOK_LINK in w]
        except gspread.WorksheetNotFound:
            print("No 'webhooks' sheet in", sheet.id)
            continue

        # Get manga IDs, filter out invalid formats
        try:
            ids = sheet.worksheet('manga').col_values(1)
            sheet_data['ids'] = [i for i in ids if re.fullmatch(REGEX, i)]
        except gspread.WorksheetNotFound:
            print("No 'manga' sheet in", sheet.id)
            continue

        result.append(sheet_data)

    return result
