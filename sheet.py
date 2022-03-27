'''
Reads whitelisted manga ID's from google sheet
'''
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# defines
SCOPE = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
SHEET = 'Mangadex'

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)

# authorize the clientsheet 
client = gspread.authorize(creds)

def get_whitelist():
    sheet = client.open(SHEET)
    sheet_instance = sheet.get_worksheet(1)
    return sheet_instance.col_values(2)


def get_webhooks():
    sheet = client.open(SHEET)
    sheet_instance = sheet.get_worksheet(0)
    return sheet_instance.col_values(1)