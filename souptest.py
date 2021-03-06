#!/usr/bin/env python3
import random
import shlex
import os
import pysrt
import flickrapi
import logging
import logging.handlers
import string
import urllib
import tweepy
import sqlite3 as lite
import sys
import youtube_dl
from bs4 import BeautifulSoup
from subprocess import call
from tumblpy import Tumblpy
from configobj import ConfigObj
from setproctitle import setproctitle

run_id = ''.join(random.choice(
        string.ascii_lowercase+string.digits) for i in range(5))

# rename the process for troubleshooting
setproctitle("souptest-"+run_id)

config = ConfigObj('api.conf')
con = lite.connect('soup.db')
cur = con.cursor()

try:
    debug_mode = config.as_bool('debug_mode')
except KeyError:
    debug_mode = False

tconf = config['tumblr']
consumer_key = tconf['consumer_key']
consumer_secret = tconf['consumer_secret']
oauth_token = tconf['oauth_token']
oauth_secret = tconf['oauth_secret']
blog = tconf['blog_host']
if not blog.startswith('http://'):
    blog = 'http://' + blog

fconf = config['flickr']
apikey = fconf['apikey']
apisecret = fconf['apisecret']
flickr = flickrapi.FlickrAPI(apikey, apisecret)

logconf = config['log']
maxBytes = int(logconf['maxBytes'])
backupCount = int(logconf['backupCount'])

client = Tumblpy(
    consumer_key,
    consumer_secret,
    oauth_token,
    oauth_secret
)

twconf = config['twitter']
tw_con_key = twconf['consumer_key']
tw_con_secret = twconf['consumer_secret']
tw_key = twconf['key']
tw_secret = twconf['secret']
tw_auth = tweepy.OAuthHandler(tw_con_key, tw_con_secret)
tw_auth.set_access_token(tw_key, tw_secret)
tw = tweepy.API(tw_auth)


# Get list of words for random queries
wordlist = []
cur.execute('SELECT * FROM Words')
words = cur.fetchall()
for each in words:
    wordlist.append(each[1])
# Build a list of photos we have already used
cur.execute('SELECT * FROM old_photos')
old_photos = cur.fetchall()
oldphotolist = {}
for each in old_photos:
    oldphotolist[each[1]] = 1

logger = logging.getLogger('souptest')
logger.setLevel(logging.DEBUG)
logger.propagate = False
fhandler = logging.handlers.RotatingFileHandler(
    os.path.join('logs', blog.split('/')[2]+'.log'),
    maxBytes=maxBytes,
    backupCount=backupCount
)
fhandler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - '+run_id+' - %(message)s')
fhandler.setFormatter(formatter)
logger.addHandler(fhandler)

if debug_mode:
    out = logging.StreamHandler(stream=sys.stdout)
    out.setFormatter(formatter)
    logger.addHandler(out)


def build_caption(quote):
    logger.info("Building caption for Tumblr")
    caption = ">`%s`" % (quote)
    return caption


def clean_quote(text):
    text_trails = True
    puncs = [".", ".", ".", "\\!", "?", "..."]
    trails = (' and', ' an', ' the', ' but', ' or', ' nor', ' a')
    while text_trails:
        text = text.strip().strip("@#$%^&*()-_=+,<>/;:'[]{}`~")
        if text.strip('.?!').endswith(trails):
            trail_len = len(text.split()[-1])
            text = text[:-trail_len]
        else:
            text_trails = False
    text = text.replace('"', '\\"')
    text = text.replace("!", "\\!")
    text = text[0].upper()+text[1:]
    if not text.endswith(('.', '!', '?', '"')):
        text += random.choice(puncs)
    elif text.endswith('"') and not text.endswith(('.\"', '\!\"', '?\"')):
        text = text[:-1] + random.choice(puncs) + '\\"'
    return text


def cleanup():
    for each in os.listdir('.'):
        if each.endswith(('.srt', '.jpg', '.vtt')):
            logger.info("Removing: "+each)
            os.remove(each)


def clear_photo(pic_id):
    logger.info("Adding photo to old_photos: " + pic_id)
    cur.execute('INSERT INTO old_photos(photo) VALUES(?)', (pic_id,))
    con.commit()
    cur.execute('DELETE FROM Photos WHERE photo_id=?', (pic_id,))
    con.commit()


def create_image(quote, pic_name, width, height):
    width = str(int(width)-100)
    height = str(int(height)-100)
    cmd = '''convert -background none -gravity center -font Helvetica \
-fill white -stroke black -strokewidth 2 -size %sx%s \
caption:"%s" \
%s +swap -gravity center -composite final.jpg''' % (width, height,
                                                    quote, pic_name)
    call(shlex.split(cmd))
    logger.info("Created overlayed text image")


def choose_tags(photo):
    phid = photo[0]
    picinfo = flickr.photos.getInfo(photo_id=phid)
    newtags = []
    for each in picinfo[0][11]:
        t = each.get('raw')
        if len(t.split(":")) > 1:
            newtags.append(t.split(":")[1])
        else:
            newtags.append(t)
    logger.info("Creating tags from Flickr tags")
    tags_select = []
    for each in newtags:
        i = each.strip().strip(
            ".!?@#$%^&*()-_=+,<>/;:'[]{}`~").strip('"').lower()
        if i.isalpha():
            tags_select.append(i)
    tagdict = {}
    taglist = []
    for i in range(1, 100):
        tag = random.choice(tags_select)
        if (
            (tag not in tagdict) and
            (len(taglist) < 5)
        ):
            tagdict[tag] = 1
            taglist.append(tag)
    tags = ''
    for each in taglist:
        tags = tags + each + ','
    tags = tags
    logger.info("Tags: "+tags)
    return tags

def get_photo():  # Picks a random photo and grabs data to give to the script.
    photos = get_photo_list()
    rand_pic = random.choice(list(photos.keys()))
    newphoto = False
    while not newphoto:
        if rand_pic in oldphotolist:
            cur.execute('DELETE FROM Photos WHERE photo_id=?', (rand_pic,))
            con.commit()
            photos = get_photo_list()
            rand_pic = random.choice(list(photos.keys()))
        else:
            newphoto = True
            url, width, height = photos[rand_pic]
    logger.info("Photo chosen: "+url)
    return str(rand_pic), url, width, height


def get_photo_archive(counter=30):  # Builds the photo archive
    logger.info("Building photo archive")
    for each in range(1, counter):
        rand_word = random.choice(wordlist)
        tagchoices = ['nature', 'landscape', 'plant', 'animal']
        photos = flickr.photos.search(
            text=rand_word,
            extras='url_l,url_o,path_alias,tags',
            license='7',
            safesearch='1',
            tags=random.choice(tagchoices), tag_mode='all', content_type='1')
        for pic in photos[0]:
            cur.execute('SELECT EXISTS(SELECT * FROM Photos WHERE photo_id=?)',
                        (pic.get('id'),))
            pic_check = cur.fetchall()[0][0]
            if (
                pic.get('pathalias') and
                (pic_check == 0)
            ):
                title = pic.get('title')
                pic_id = pic.get('id')
                user = pic.get('pathalias')
                if not pic.get('url_l'):
                    url = pic.get('url_o')
                    width = pic.get('width_o')
                    height = pic.get('height_o')
                else:
                    url = pic.get('url_l')
                    width = pic.get('width_l')
                    height = pic.get('height_l')
                tags = pic.get('tags').replace(' ', ',')
                cur.execute("""
                INSERT INTO Photos(photo_id, user, url, width, height, tags)
                VALUES(?, ?, ?, ?, ?, ?)""",
                            (pic_id, user, url, width, height, tags))
                con.commit()


def get_photo_list():
    logger.info('Building photo list')
    cur.execute('SELECT * FROM Photos')
    photos = cur.fetchall()
    photo_archive = {}
    for each in photos:
        (db_id, photo_id, user, url, width,
         height, tags) = each
        photo_archive[photo_id] = (url, width, height)
    return photo_archive


def get_subs(yt_links):
    has_subtitles = False
    x = 1
    while not has_subtitles:
        logger.debug("Starting loop: " + str(x))
        if yt_links:
            chosen_key = random.choice(list(yt_links.keys()))
            logger.debug(chosen_key)
            chosen_one = yt_links[chosen_key]
            ydl_opts = {
                'quiet': True,
	            'no_warnings': True,
	            'noplaylist': True,
	            'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ["en"],
                'skip_download': True,
                'restrictfilenames': True,
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([chosen_one])
            contents = os.listdir('.')
            for each in contents:
                # Look for .vtt files because of issue #9073 in youtube-dl
                if each.endswith('.vtt'):
                    convertCommand = "ffmpeg -i " + each + " " + each + ".srt"
                    with open(os.devnull, "w") as f:
                        call(shlex.split(convertCommand), stdout=f, stderr=f)
                    subFile = each + ".srt"
                    subs = pysrt.open(subFile)
                    has_subtitles = True
                    logger.info("Chosen YT video: "+chosen_one)
            if not has_subtitles:
                logger.debug("no subs - " + str(x))
                yt_links.pop(chosen_key)
        else:
            logger.debug("get videos - " + str(x))
            yt_links = get_videos()
        x += 1
    return subs


def get_videos():  # Gets videos by scraping the youtube search page for links
    logger.info("Getting list of YouTube videos")
    rand_word = random.choice(wordlist)
    results = urllib.urlopen(
        'https://www.youtube.com/results?search_query=' + rand_word).read()
    soup = BeautifulSoup(results, "lxml")
    yt_links = {}
    for link in soup.find_all('a'):
        x = link.get('href')
        if x.startswith('/watch?') and x not in yt_links:
            yt_links[x] = 'https://www.youtube.com'+x
    return yt_links


# Translate is broke half the time so I'm improvising.
def rand_quote(subs):
    long_enough = False
    x = 0
    while not long_enough:
        if x == 10:
            cleanup()
            yt_links = get_videos()
            subs = get_subs(yt_links)
            x = 0
        subsection = random.choice(subs)
        quote = subsection.text.replace('\n', ' ')
        final_quote = clean_quote(quote)
        if (len(final_quote.split()) > 6) and (len(final_quote.split()) < 15):
            logger.info("Cleaning this text: "+quote)
            long_enough = True
        x += 15
    logger.info("Used quote: "+final_quote)
    return final_quote


def tumblr_post(pic, caption, pictags=None,
                flickr=None, post_state='queue', tformat='markdown'):
    caption = caption.replace("\\", "")
    logger.info("Posting to Tumblr")
    picdata = open(pic, 'rb')
    tparams = {
        'state': post_state,
        'type': 'photo',
        'format': tformat,
        'caption': caption,
        'data': picdata
    }
    if pictags:
        tparams['tags'] = pictags + run_id
    if flickr:
        tparams['link'] = flickr
    client.post('post', blog_url=blog, params=tparams)


def twitter_post(pic, caption, tags):
    tagList = tags.strip(",").split(',')
    tag = random.choice(tagList)
    caption = caption.replace('\\', '')
    caption = caption + " #" + tag
    logger.info("Posting to twitter: " + caption)
    tw.update_with_media(pic, status=caption)


def main():
    # Pick a video with subtitles to gather random text from
    yt_links = get_videos()
    subs = get_subs(yt_links)
    # Time to pick our text from the subs
    final_quote = rand_quote(subs)
    # Pick a random photo and make sure it is one we haven't used before
    try:
        rand_pic, url, width, height = get_photo()
    except:
        get_photo_archive()
        rand_pic, url, width, height = get_photo()
    # Download and add text to photo
    urllib.urlretrieve(url, rand_pic+'.jpg')
    create_image(final_quote, rand_pic+'.jpg', width, height)
    # Build info for tumblr
    cur.execute('SELECT * FROM Photos WHERE photo_id=?', (rand_pic,))
    photo = cur.fetchone()[1:]
    # Make some tags! Gotta promote through randomness!
    tags = choose_tags(photo)
    caption = build_caption(final_quote)
    link = 'https://www.flickr.com/'+photo[1]+'/'+rand_pic
    # tumblr_post('final.jpg', caption, pictags=tags, flickr=link)
    twitter_post('final.jpg', final_quote, tags)
    # Clean up after myself
    clear_photo(rand_pic)
    cleanup()


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception("An error occurred.")
        cleanup()
