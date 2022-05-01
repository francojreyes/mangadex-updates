'''
Access github file storage to get and set time of last check
'''
import os
import traceback
from datetime import datetime

from dotenv import load_dotenv
from github import Github

load_dotenv()

last_check_str = None

try:
    github = Github(os.getenv('GITHUB_ACCESS_TOKEN'))
    repo = github.get_user().get_repo('mangadex-updates')

    f = repo.get_contents('last_check.txt')
    last_check_str = f.decoded_content.decode()
except:
    traceback.print_exc()

if last_check_str:
    new_time = datetime.now().isoformat(timespec='seconds')
    repo.update_file(f.path, "Updated last check time", new_time, f.sha)


