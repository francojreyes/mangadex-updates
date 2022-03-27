'''
Needed to update old manga IDs to new UUIDs
'''
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# defines
SCOPE = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
SHEET = 'Mangadex'

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)

# authorize the clientsheet 
client = gspread.authorize(creds)

sheet = client.open(SHEET)
sheet_instance = sheet.get_worksheet(1)
old_ids = sheet_instance.col_values(1)

new_ids = []
for old_id in old_ids:
    response = requests.get('https://mangadex.org/title/' + old_id)
    new_id = response.url.split('/')[-1]
    new_ids.append(new_id)
    print(old_id, "redirected to", new_id)

sheet_instance.insert_cols([new_ids], col=2)