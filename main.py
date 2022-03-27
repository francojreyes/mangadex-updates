'''
Main file that makes requests to mangadex API and sends embeds to webhook
'''
import sheet
import requests
import time
import json
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook, DiscordEmbed

# Important URLs
API_URL = 'https://api.mangadex.org/'

# Time between each check (in hours)
INTERVAL = 12
UTC_OFFSET = 11


def check_updates():
    '''
    Get and send all manga updates
    '''
    # Determine time of last check
    last_check = datetime.now() - timedelta(hours=INTERVAL)
    query_updatedAtSince = last_check.strftime("%Y-%m-%dT%H:%M:%S")

    # Set parameters for manga search query
    query_params = {
        # 'limit': 100,
        'updatedAtSince': query_updatedAtSince,
        # 'availableTranslatedLanguage[0]': 'en'
    }

    # Get list of manga IDs from Google Sheet
    # ids = sheet.get_whitelist()
    # for i in range(len(ids)):
    #   query_params[f"ids[{i}]"] = ids[i]
    
    try:
        mangas = requests.get(f'{API_URL}manga', params=query_params).json()['data']
    except Exception as error:
        print('Could not get manga:', error)
        return

    with open('list.json', 'w') as f:
        json.dump(mangas, f, indent=4)

    for manga in mangas:
        # Get all English chapters updated since last check
        try:
            chapters = requests.get(f'{API_URL}chapter', params={
                'manga': manga['id'],
                'updatedAtSince': query_updatedAtSince,
                'translatedLanguage[0]': 'en'
            }).json()['data']
        except Exception as error:
            print('Could not get chapters:', error)
            return

        if len(chapters) == 0:
            print(f"No chapters for {manga['id']}")

        for chapter in chapters:
            send_webhooks(manga, chapter)


def send_webhooks(manga, chapter):
    '''
    Send a webhook for the given chapter to all webhooks listed in Google Sheet
    '''
    for webhook in sheet.get_webhooks():
        # Get manga data
        manga_url = 'https://mangadex.org/title/' + manga['id']
        title = get_title(manga)
        if title is None:
            return

        # Get chapter data
        chapter_url = 'https://mangadex.org/chapter/' + chapter['id']
        description = get_description(chapter)
        time_updated = datetime.strptime(chapter['attributes']['updatedAt'], '%Y-%m-%dT%H:%M:%S+00:00')
        time_updated += timedelta(hours=11)
        
        # Send webhook to discord
        webhook = DiscordWebhook(url=webhook, username='MangaDex')
        embed = DiscordEmbed(
            title= title,
            url=manga_url,
            description=f"[{description}]({chapter_url})",
            color='f69220'
        )
        embed.set_timestamp(time_updated.timestamp())
        webhook.add_embed(embed)

        try:
            webhook.execute()
        except Exception as error:
            print('Could not send webhook:', error)


def get_title(manga):
    '''
    Search both title fields for English title. If None, return None.
    '''
    attributes = manga['attributes']
    if 'en' in attributes['title']:
        return attributes['title']['en']
    elif 'en' in attributes['altTitles']:
        return attributes['altTitles']['en']
    else:
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
    elif attributes['chapter']:
        return f"Chapter {attributes['chapter']}"
    else:
        return "Oneshot"




if __name__ == '__main__':
    while True:
        check_updates()
        time.sleep(3600 * INTERVAL)