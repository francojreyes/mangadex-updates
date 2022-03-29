'''
Main file that makes requests to mangadex API and sends embeds to webhook
'''
import time
import traceback
from datetime import datetime, timedelta
from urllib.error import HTTPError

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

import sheet


# Important URLs
API_URL = 'https://api.mangadex.org/'

# Time between each check (in hours)
INTERVAL = 1

def check_updates():
    '''
    Get and send all manga updates
    '''
    # Read data from google sheets
    manga_ids = sheet.get_whitelist()
    webhooks = sheet.get_webhooks()
    # Determine time of last check
    last_check = datetime.now() - timedelta(hours=INTERVAL)
    print("Checking since", last_check.strftime("%Y-%m-%dT%H:%M:%S"))

    # Get all English chapters updated since last check
    query_params = {
        'limit': 100,
        'offset': 0,
        'updatedAtSince': last_check.strftime("%Y-%m-%dT%H:%M:%S"),
        'translatedLanguage[0]': 'en',
    }
    try:
        response = requests.get(f'{API_URL}chapter', params=query_params).json()
    except HTTPError:
        traceback.print_exc()
        return

    chapters = response['data']
    while response['total'] > response['limit']:
        query_params['offset'] += response['limit']
        try:
            response = requests.get(f'{API_URL}chapter', params=query_params).json()
        except HTTPError:
            traceback.print_exc()
            return
        chapters += response['data']
    

    for chapter in chapters:
        # Ensure chapter is actually new
        if not is_new(last_check, chapter):
            print('No actual update for', chapter['id'])
            continue

        # Check if manga is in whitelist
        manga = get_manga(chapter)
        if manga is None:
            print('No manga found for', chapter['id'])
            continue
        if manga['id'] not in manga_ids:
            print(get_title(manga), f"({manga['id']})", 'is not in list')
            continue

        for webhook in webhooks:
            print('Sending webhook for', chapter['id'])
            send_webhook(webhook, manga, chapter)


def send_webhook(webhook, manga, chapter):
    '''
    Send an embed to the given webhook URL about the given chapter of manga
    '''
    # Get manga data
    manga_url = 'https://mangadex.org/title/' + manga['id']
    title = get_title(manga)
    cover_art_url = get_cover_url(manga)

    # Get chapter data
    chapter_url = get_chapter_url(chapter)
    description = generate_description(chapter)
    time_updated = datetime.strptime(
        chapter['attributes']['readableAt'], '%Y-%m-%dT%H:%M:%S+00:00')

    # Send webhook to discord
    webhook = DiscordWebhook(url=webhook, username='MangaDex')
    embed = DiscordEmbed(
        title=title,
        url=manga_url,
        description=f"[{description}]({chapter_url})",
        color='f69220'
    )
    embed.set_thumbnail(url=cover_art_url)
    embed.set_timestamp(time_updated.timestamp())
    webhook.add_embed(embed)

    try:
        webhook.execute()
    except HTTPError:
        traceback.print_exc()


def get_title(manga):
    '''
    Return main title
    '''
    return list(manga['attributes']['title'].values())[0]


def generate_description(chapter):
    '''
    Find volume and chapter numbers.
    If volume is none, return chapter only.
    If both none, oneshot.
    '''
    attributes = chapter['attributes']
    if attributes['volume']:
        return f"Volume {attributes['volume']}, Chapter {attributes['chapter']}"

    if attributes['chapter']:
        return f"Chapter {attributes['chapter']}"

    return "Oneshot"


def get_manga(chapter):
    '''
    Get the manga attached to the given chapter
    '''
    for relationship in chapter['relationships']:
        if relationship['type'] == 'manga':
            break
    else:
        return None

    try:
        response = requests.get(f"{API_URL}manga/{relationship['id']}")
        return response.json()['data']
    except HTTPError:
        traceback.print_exc()
        return None


def get_cover_url(manga):
    '''
    Get the url for the cover art of the given manga
    '''
    for relationship in manga['relationships']:
        if relationship['type'] == 'cover_art':
            break
    else:
        return None

    try:
        response = requests.get(f"{API_URL}cover/{relationship['id']}")
    except HTTPError:
        traceback.print_exc()
        return None

    cover = response.json()['data']['attributes']
    return f"https://uploads.mangadex.org/covers/{manga['id']}/{cover['fileName']}"


def get_chapter_url(chapter):
    '''
    Return external URL if exists, or mangadex url otherwise
    '''
    if chapter['externalUrl']:
        return chapter['externalUrl']

    return 'https://mangadex.org/chapter/' + chapter['id']


def is_new(last_check, chapter):
    '''
    Compare time posted (readableAt) against time of last check
    to determine if the detected update was the chapter being posted or not
    '''
    last_updated = datetime.strptime(
        chapter['attributes']['readableAt'], '%Y-%m-%dT%H:%M:%S+00:00')
    return last_check < last_updated


if __name__ == '__main__':
    while True:
        check_updates()
        time.sleep(3600 * INTERVAL)