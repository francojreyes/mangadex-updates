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
    print(f"sheet read executed in {elapsed:0.2f} seconds.")

    # Determine time of last check
    last_check = datetime.now() - timedelta(hours=INTERVAL)
    last_check_str = last_check.strftime("%Y-%m-%dT%H:%M:%S")
    print("Checking since", last_check_str)

    # Get all English chapters updated since last check
    chapters = request_chapters(last_check_str)
    for chapter in chapters:
        # Ensure chapter is actually new
        if get_time_posted(chapter) < last_check:
            print('No real update for', chapter['id'])
            continue

        # Gather webhooks for all sheets containing this chapter
        # If none exist, continue
        manga_id = get_manga_id(chapter)
        webhooks = list(itertools.chain(*[s['webhooks'] for s in sheets if manga_id in s['ids']]))
        if len(webhooks) == 0:
            print('No sheets containing manga of', chapter['id'])
            continue

        # Create the embed
        manga = request_manga(manga_id)
        embed = create_embed(manga, chapter)

        # Send the embed to each webhook
        print('Sending webhooks for', chapter['id'])
        for webhook in webhooks:
            webhook = DiscordWebhook(
                url=webhook,
                username='MangaDex',
                avatar_url=MANGADEX_LOGO,
                embeds=[embed]
            )

            try:
                webhook.execute()
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
    }

    chapters = []
    while True:
        try:
            response = requests.get(f'{API_URL}chapter', params=query_params).json()
        except:
            traceback.print_exc()
            return
        chapters += response['data']

        # If no more chapters
        if response['total'] - response['offset'] <= response['limit']:
            break

        query_params['offset'] += response['limit']

    return chapters     


def create_embed(manga, chapter):
    '''
    Create an embed for the given chapter of manga
    '''
    # Get manga data
    manga_url = 'https://mangadex.org/title/' + manga['id']
    manga_title = list(manga['attributes']['title'].values())[0]

    # Get chapter data
    chapter_url = get_chapter_url(chapter)
    description = generate_description(chapter)
    og_image = 'https://og.mangadex.org/og-image/chapter/' + chapter['id']
    time_posted = get_time_posted(chapter)

    # Create the embed
    embed = DiscordEmbed(
        color='f69220',
        title=manga_title,
        url=manga_url,
        description=f"[{description}]({chapter_url})",
        image=og_image,
        footer='New chapter available',
        timestamp=time_posted.timestamp()
    )

    return embed


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


def get_manga_id(chapter):
    '''
    Get the ID of the manga attached to the given chapter
    '''
    for relationship in chapter['relationships']:
        if relationship['type'] == 'manga':
            return relationship['id']

    return None


def request_manga(manga_id):
    '''
    Request the manga with the given ID
    '''
    try:
        response = requests.get(f"{API_URL}manga/{manga_id}")
        return response.json()['data']
    except:
        traceback.print_exc()
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
