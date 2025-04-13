"""
Functions to read manga/webhook data and read/write time data
"""
import os
import re
from datetime import datetime

import backoff
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# defines
SCOPE = ['https://www.googleapis.com/auth/spreadsheets.readonly',
         'https://www.googleapis.com/auth/drive.readonly']
ID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
LANG_REGEX = r'^[a-z]{2}(-[a-z]{2})?$'
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
gclient = gspread.authorize(creds)

# connect to mongodb
mclient = MongoClient(os.getenv('MONGODB_URL'), server_api=ServerApi('1'))
db = mclient.mangadex


@backoff.on_exception(backoff.fibo, gspread.exceptions.APIError)
def open_all_sheets():
    return gclient.openall()


@backoff.on_exception(backoff.fibo, gspread.exceptions.APIError)
def read_worksheet(sheet: gspread.Spreadsheet, worksheet_name: str, range_name: str) -> list[list[str]]:
    return sheet.worksheet(worksheet_name).get_values(range_name)


def get_sheets():
    """
    Scan all sheets and return the list of webhooks/ids
    Ignores sheets with invalid format
    """
    sheets = open_all_sheets()

    result = []
    for sheet in sheets:
        sheet_data = {
            'id': sheet.id
        }

        # Get webhooks, filter out invalid links
        try:
            webhooks = read_worksheet(sheet, 'webhooks', "A:A")
            sheet_data['webhooks'] = [w[0] for w in webhooks if WEBHOOK_LINK in w]
        except gspread.WorksheetNotFound:
            print("No 'webhooks' sheet in", sheet.id)
            continue

        # Get manga IDs, filter out invalid formats
        try:
            rows = read_worksheet(sheet, 'manga', "A:B")
            sheet_data['manga'] = {}
            for row in rows:
                if not re.fullmatch(ID_REGEX, row[0]):
                    continue
                languages = row[1] if len(row) >= 2 and row[1] else "en"
                sheet_data['manga'][row[0]] = [lang for lang in re.split("\s*,\s*", languages) if
                                               re.fullmatch(LANG_REGEX, lang)]
        except gspread.WorksheetNotFound:
            print("No 'manga' sheet in", sheet.id)
            continue

        result.append(sheet_data)

    return result


def get_time():
    """
    Get last check time
    """
    return db.last_check.find_one(
        {'_id': 0},
        {'time': True, '_id': False}
    )['time']


def set_time():
    """
    Set last check time to now
    """
    db.last_check.find_one_and_update(
        {'_id': 0},
        {'$set': {'time': datetime.now().isoformat(timespec='seconds')}}
    )
