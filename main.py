"""
Main file that makes requests to mangadex API and sends embeds to webhook
"""
import time
import traceback
from collections import defaultdict
from datetime import datetime

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook

import data

# Important URLs
API_URL = 'https://api.mangadex.org/'
MANGADEX_LOGO = 'https://pbs.twimg.com/profile_images/1391016345714757632/xbt_jW78_400x400.jpg'
LOGO = 'https://raw.githubusercontent.com/francojreyes/mangadex-updates/master/icon.png'

def check_updates():
    """
    Get and send all manga updates
    """
    # Read data from Google sheets
    s = time.perf_counter()
    sheets = data.get_sheets()
    elapsed = time.perf_counter() - s
    print(f"Read {len(sheets)} sheets in {elapsed:0.2f} seconds.")

    # Group webhooks by (manga, lang)
    webhook_map = defaultdict(list)
    for sheet in sheets:
        for manga, langs in sheet["manga"].items():
            for lang in langs:
                webhook_map[(manga, lang)].extend(sheet["webhooks"])

    # Get all English chapters updated since last check
    last_check_str = data.get_time()
    print('Checking since', last_check_str)
    last_check_dt = datetime.fromisoformat(last_check_str)
    chapters = request_chapters(last_check_str)
    for chapter in chapters:
        # Ensure chapter is actually new
        time_posted = get_time_posted(chapter)
        if time_posted < last_check_dt:
            continue

        # Gather webhooks for all sheets containing this chapter's manga
        manga = get_manga(chapter)
        language = chapter['attributes']['translatedLanguage']
        webhooks = webhook_map[(manga['id'], language)]

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
            timestamp=time_posted.isoformat()
        )

        # Send the embed to each webhook
        print(f"Sending {len(webhooks)} webhooks for {embed.description}")
        try:
            DiscordWebhook(
                url=webhooks,
                username='MangaDex',
                avatar_url=LOGO,
                embeds=[embed],
                rate_limit_retry=True
            ).execute()
        except:
            traceback.print_exc()


def request_chapters(last_check_str):
    """
    Request all English chapters updated since last_check
    """
    query_params = {
        'limit': 100,
        'offset': 0,
        'updatedAtSince': last_check_str,
        'includes[0]': 'manga',
    }

    s = time.perf_counter()
    chapters = []
    while True:
        response = requests.get(
            f'{API_URL}chapter', params=query_params).json()
        time.sleep(1/5)
        chapters += response['data']

        # If no more chapters
        if response['total'] - response['offset'] <= response['limit']:
            break

        query_params['offset'] += response['limit']

    elapsed = time.perf_counter() - s
    print(f"Read {len(chapters)} chapters in {elapsed:0.2f} seconds.")
    return chapters


def generate_description(chapter):
    """
    Find volume and chapter numbers.
    If volume is none, return chapter only. If both none, oneshot.
    Append title if it exists.
    """
    attributes = chapter['attributes']
    result = f"[{attributes['translatedLanguage']}] "
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
    """
    Get the manga related to the given chapter
    """
    for relationship in chapter['relationships']:
        if relationship['type'] == 'manga':
            return relationship

    return None


def get_chapter_url(chapter):
    """
    Return external URL if exists, or mangadex url otherwise
    """
    if chapter['attributes']['externalUrl']:
        return chapter['attributes']['externalUrl']

    return 'https://mangadex.org/chapter/' + chapter['id']


def get_time_posted(chapter):
    """
    Return datetime object corresponding to time chapter was posted.
    """
    if chapter['attributes']['readableAt']:
        return datetime.strptime(
            chapter['attributes']['readableAt'], '%Y-%m-%dT%H:%M:%S+00:00')
    else:
        return datetime.strptime(
            chapter['attributes']['createdAt'], '%Y-%m-%dT%H:%M:%S+00:00')


if __name__ == '__main__':
    check_updates()
    data.set_time()
