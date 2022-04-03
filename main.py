'''
Main file that makes requests to mangadex API and sends embeds to webhook
'''
import itertools
import time
import traceback
from datetime import datetime, timedelta

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

import sheet_reader

# Important URLs
API_URL = 'https://api.mangadex.org/'
MANGADEX_LOGO = 'https://pbs.twimg.com/profile_images/1391016345714757632/xbt_jW78_400x400.jpg'

# Time between each check (in hours)
INTERVAL = 1


def check_updates():
    '''
    Get and send all manga updates
    '''
    # Read data from google sheets
    s = time.perf_counter()
    sheets = sheet_reader.get_sheets()
    elapsed = time.perf_counter() - s
    print(f"Read {len(sheets)} sheets in {elapsed:0.2f} seconds.")

    # Determine time of last check
    last_check = datetime.now() - timedelta(hours=INTERVAL)
    last_check_str = last_check.isoformat(timespec='seconds')
    print("Checking since", last_check_str)

    # Get all English chapters updated since last check
    chapters = request_chapters(last_check_str)
    for chapter in chapters:
        # Ensure chapter is actually new
        if get_time_posted(chapter) < last_check:
            continue

        # Gather webhooks for all sheets containing this chapter's manga
        manga = get_manga(chapter)
        webhooks = list(itertools.chain(
            *[sheet['webhooks'] for sheet in sheets if manga['id'] in sheet['ids']]))
        # If none exist, continue
        if len(webhooks) == 0:
            continue

        # Create the embed
        embed = DiscordEmbed(
            hcolor='f69220',
            title=list(manga['attributes']['title'].values())[0],
            url='https://mangadex.org/title/' + manga['id'],
            description=f"[{generate_description(chapter)}]({get_chapter_url(chapter)})",
            image={'url': 'https://og.mangadex.org/og-image/chapter/' + chapter['id']},
            footer={'text': 'New chapter available'},
            timestamp=get_time_posted(chapter).isoformat()
        )

        # Send the embed to each webhook
        print('Sending webhooks for', chapter['id'])
        try:
            DiscordWebhook(
                url=webhooks,
                username='MangaDex',
                avatar_url=MANGADEX_LOGO,
                embeds=[embed]
            ).execute()
        except:
            traceback.print_exc()


def request_chapters(last_check_str):
    '''
    Request all English chapters updated since last_check
    '''
    query_params = {
        'limit': 100,
        'offset': 0,
        'updatedAtSince': last_check_str,
        'translatedLanguage[0]': 'en',
        'includes[0]': 'manga',
    }

    chapters = []
    while True:
        try:
            response = requests.get(
                f'{API_URL}chapter', params=query_params).json()
            time.sleep(1/5)
        except:
            traceback.print_exc()
            break
        chapters += response['data']

        # If no more chapters
        if response['total'] - response['offset'] <= response['limit']:
            break

        query_params['offset'] += response['limit']

    return chapters


def generate_description(chapter):
    '''
    Find volume and chapter numbers.
    If volume is none, return chapter only. If both none, oneshot.
    Append title if it exists.
    '''
    result = ''

    attributes = chapter['attributes']
    if attributes['volume']:
        result += f"Volume {attributes['volume']}, Chapter {attributes['chapter']}"
    elif attributes['chapter']:
        result += f"Chapter {attributes['chapter']}"
    else:
        result += "Oneshot"

    if attributes['title']:
        result += f" - {attributes['title']}"

    return result


def get_manga(chapter):
    '''
    Get the manga related to the given chapter
    '''
    for relationship in chapter['relationships']:
        if relationship['type'] == 'manga':
            return relationship

    return None


def get_chapter_url(chapter):
    '''
    Return external URL if exists, or mangadex url otherwise
    '''
    if chapter['attributes']['externalUrl']:
        return chapter['attributes']['externalUrl']

    return 'https://mangadex.org/chapter/' + chapter['id']


def get_time_posted(chapter):
    '''
    Return datetime object corresponding to time chapter was posted
    '''
    return datetime.strptime(
        chapter['attributes']['readableAt'], '%Y-%m-%dT%H:%M:%S+00:00')


if __name__ == '__main__':
    while True:
        check_updates()
        time.sleep(3600 * INTERVAL)
