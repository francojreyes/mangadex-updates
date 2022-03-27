'''
Main file that makes requests to mangadex API and sends embeds to webhook
'''
import time
from datetime import datetime, timedelta
from urllib.error import HTTPError

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

import sheet

# Important URLs
API_URL = 'https://api.mangadex.org/'

# Time between each check (in hours)
INTERVAL = 1
UTC_OFFSET = 11


def check_updates():
    '''
    Get and send all manga updates
    '''
    # Read data from google sheets
    manga_ids = sheet.get_whitelist()
    webhooks = sheet.get_webhooks()

    # Determine time of last check
    last_check = datetime.now() - timedelta(hours=INTERVAL)

    # Get all English chapters updated since last check
    try:
        response = requests.get(f'{API_URL}chapter', params={
            'updatedAtSince': last_check.strftime("%Y-%m-%dT%H:%M:%S"),
            'translatedLanguage[0]': 'en'
        })
    except HTTPError as error:
        print('Could not get chapters:', error)
        return

    chapters = response.json()['data']

    for chapter in chapters:
        manga = get_manga(chapter)
        if manga is None:
            continue

        for webhook in webhooks:
            send_webhook(webhook, manga, chapter)


def send_webhook(webhook, manga, chapter):
    '''
    Send an embed to the given webhook URL about the given chapter of manga
    '''
    # Get manga data
    manga_url = 'https://mangadex.org/title/' + manga['id']
    title = get_title(manga)
    if title is None:
        return
    cover_art_url = get_cover_url(manga)

    # Get chapter data
    chapter_url = 'https://mangadex.org/chapter/' + chapter['id']
    description = get_description(chapter)
    time_updated = datetime.strptime(
        chapter['attributes']['updatedAt'], '%Y-%m-%dT%H:%M:%S+00:00')
    time_updated += timedelta(hours=UTC_OFFSET)

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
    except HTTPError as error:
        print('Could not send webhook:', error)


def get_title(manga):
    '''
    Search both title fields for English title. If None, return None.
    '''
    attributes = manga['attributes']
    if 'en' in attributes['title']:
        return attributes['title']['en']

    if 'en' in attributes['altTitles']:
        return attributes['altTitles']['en']

    return None


def get_description(chapter):
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
    except HTTPError as error:
        print(error)
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
    except HTTPError as error:
        print(error)
        return None

    cover = response.json()['data']['attributes']
    return f"https://uploads.mangadex.org/covers/{manga['id']}/{cover['fileName']}"


if __name__ == '__main__':
    while True:
        check_updates()
        time.sleep(3600 * INTERVAL)
