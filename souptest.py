#!/usr/bin/env python3
import random
import shlex
import os
import pysrt
import goslate
import flickrapi
import logging
import logging.handlers
import string
import urllib.request
import tweepy
import sqlite3 as lite
from bs4 import BeautifulSoup
from subprocess import call
from tumblpy import Tumblpy
from configobj import ConfigObj

config = ConfigObj('api.conf')
gs = goslate.Goslate()
con = lite.connect('soup.db')
cur = con.cursor()

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
# Build list of languages accepted by goslate
cur.execute('SELECT * FROM Languages')
languages = cur.fetchall()
langs = {}
for each in languages:
    langs[each[1]] = each[2]
langs.pop('en')
rand_lang = random.choice(list(langs.keys()))
# Build a list of photos we have already used
cur.execute('SELECT * FROM old_photos')
old_photos = cur.fetchall()
photolist = {}
for each in old_photos:
    photolist[each[1]] = 1
# List of words that don't make for good tags
cur.execute('SELECT * FROM Bantags')
banned = cur.fetchall()
banned_tags = {}
for each in banned:
    banned_tags[each[1]] = 1
# List of users banned by me
cur.execute('SELECT * FROM Banusers')
banned = cur.fetchall()
banned_users = {}
for each in banned:
    banned_users[each[1]] = 1

run_id = ''.join(random.choice(
        string.ascii_lowercase+string.digits) for i in range(5))

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


def build_caption(photo, quote, ptype="flickr", puser=""):
    logger.info("Building caption for Tumblr")
    if photo:
        (photo_id, user, pic_url, width,
         height, title, owner, license, tags) = photo
        cur.execute('SELECT * FROM Licenses WHERE lic_id=?', (license,))
        lic, lic_url = cur.fetchone()[2:]
        profile = 'https://www.flickr.com/photos/'+user
        flickr = 'https://www.flickr.com/'+user+'/'+str(photo_id)
    else:
        lic = None
    if lic == 'NONE' and ptype == "flickr":
        caption = """>`%s`

Photo: [%s](%s) from [%s](%s)""" % (quote, title, flickr, owner, profile)
        return caption, flickr
    elif ptype == "flickr":
        caption = """>`%s`

Photo: [%s](%s) by [%s](%s) licensed under [%s](%s)""" % (quote, title, flickr,
                                                          owner, profile, lic,
                                                          lic_url)
        return caption, flickr
    if ptype == "submit":
        caption = """>`%s`

Photo submitted by %s""" % (quote, puser)
        return caption
    if ptype == "quote":
        caption = ">`%s`" % (quote)
        return caption, flickr


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


def flickr_tags(photo):
    phid, user, url, width, height, title, owner, lic, tagsraw = photo
    picinfo = flickr.photos.getInfo(photo_id=phid)
    newtags = []
    for each in picinfo[0][11]:
        newtags.append(each.get('raw'))
    logger.info("Creating tags from Flickr tags: " + url)
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
            (tag not in banned_tags) and
            (len(taglist) < 5)
        ):
            tagdict[tag] = 1
            taglist.append(tag)
    tags = ''
    for each in taglist:
        tags = tags + each + ','
    tags = tags + run_id
    logger.info("Tags: "+tags)
    return tags


def get_photo():  # Picks a random photo and grabs data to give to the script.
    photos = get_photo_list()
    rand_pic = random.choice(list(photos.keys()))
    url, width, height = photos[rand_pic]
    logger.info("Photo chosen: "+url)
    return str(rand_pic), url, width, height


def get_photo_archive(counter=30):  # Builds the photo archive
    logger.info("Building photo archive")
    tagchoices = ['landscape', 'nature']
    for each in range(1, counter):
        rand_word = random.choice(wordlist)
        photos = flickr.photos.search(
            text=rand_word,
            extras='url_l,url_o,path_alias,owner_name,license,tags',
            license='7',
            safesearch='1',
            tags=random.choice(tagchoices), tag_mode='all', content_type='1')
        for pic in photos[0]:
            cur.execute('SELECT EXISTS(SELECT * FROM Photos WHERE photo_id=?)',
                        (pic.get('id'),))
            pic_check = cur.fetchall()[0][0]
            if (
                pic.get('pathalias') and
                (pic_check == 0) and
                (pic.get('pathalias') not in banned_users)
            ):
                title = pic.get('title')
                pic_id = pic.get('id')
                user = pic.get('pathalias')
                owner = pic.get('ownername')
                if not pic.get('url_l'):
                    url = pic.get('url_o')
                    width = pic.get('width_o')
                    height = pic.get('height_o')
                else:
                    url = pic.get('url_l')
                    width = pic.get('width_l')
                    height = pic.get('height_l')
                tags = pic.get('tags').replace(' ', ',')
                license = int(pic.get('license'))
                cur.execute("""
                INSERT INTO Photos(photo_id, user, url, width, height, title,
                owner, license, tags)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (pic_id, user, url, width, height, title, owner,
                             license, tags))
                con.commit()


def get_photo_list():
    logger.info('Building photo list')
    cur.execute('SELECT * FROM Photos')
    photos = cur.fetchall()
    photo_archive = {}
    for each in photos:
        (db_id, photo_id, user, url, width,
         height, title, owner, lic, tags) = each
        photo_archive[photo_id] = (url, width, height)
    return photo_archive


def get_subs(yt_links):
    has_subtitles = False
    while not has_subtitles:
        if yt_links:
            chosen_key = random.choice(list(yt_links.keys()))
            chosen_one = yt_links[chosen_key]
            command = ("""/usr/local/bin/youtube-dl -q --no-warnings\
            --no-playlist --write-sub --write-auto-sub --sub-lang "en"\
            --skip-download "%s" --restrict-filenames""" % (chosen_one,))
            call(shlex.split(command))
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
                yt_links.pop(chosen_key)
        else:
            yt_links = get_videos()
    return subs


def get_videos():  # Gets videos by scraping the youtube search page for links
    logger.info("Getting list of YouTube videos")
    rand_word = random.choice(wordlist)
    results = urllib.request.urlopen(
        'https://www.youtube.com/results?search_query=' + rand_word).read()
    soup = BeautifulSoup(results, "lxml")
    yt_links = {}
    for link in soup.find_all('a'):
        x = link.get('href')
        if x.startswith('/watch?') and x not in yt_links:
            yt_links[x] = 'https://www.youtube.com'+x
    return yt_links


def make_tags(quote, length=5):
    logger.info("Creating tags from quote: " + quote)
    tags_split = quote.split()
    tags_select = []
    for each in tags_split:
        i = each.strip().strip(".!?@#$%^&*()-_=+,<>/;:'[]{}`~")
        i = i.strip('"').lower()
        if i:
            tags_select.append(i)
    tagdict = {}
    taglist = []
    for i in range(1, 100):
        tag = random.choice(tags_select)
        if (
            (tag not in tagdict) and
            (tag not in banned_tags) and
            (len(taglist) < length)
        ):
            tagdict[tag] = 1
            taglist.append(tag)
    tags = ''
    for each in taglist:
        tags = tags + each + ','
    tags = tags + run_id
    logger.info("Tags: " + tags)
    return tags


# Translate is broke half the time so I'm improvising.
def quote_fallback(subs):
    logger.error("Falling back to just picking a random quote")
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


def sub_translate(subs):
    logger.info("Translating from subtitle file")
    long_enough = False
    x = 0
    while not long_enough:
        if x == 10:
            cleanup()
            yt_links = get_videos()
            subs = get_subs(yt_links)
            x = 0
        rand_section = random.choice(subs)
        rand_quote = rand_section.text.replace('\n', ' ')
        translation = gs.translate(str(rand_quote), rand_lang).encode('utf-8')
        retranslate = gs.translate(translation, 'en')
        final_quote = clean_quote(retranslate)
        if (len(final_quote.split()) > 6) and (len(final_quote.split()) < 15):
            logger.info("Translating this text: "+rand_quote)
            logger.info("Cleaning this text: "+retranslate)
            long_enough = True
        x += 1
    logger.info("Translated: "+final_quote)
    return final_quote


def translate_text(quote):
    logger.info("Translating given text: " + quote)
    translation = gs.translate(quote, rand_lang).encode('utf-8')
    retranslate = gs.translate(translation, 'en')
    final_quote = clean_quote(retranslate)
    logger.info("Translated: " + final_quote)
    return final_quote


def tumblr_post(pic, caption, pictags=None,
                flickr=None, state='queue', tformat='markdown'):
    caption = caption.replace("\\", "")
    logger.info("Posting to Tumblr")
    picdata = open(pic, 'rb')
    tparams = {
        'state': state,
        'type': 'photo',
        'format': tformat,
        'caption': caption,
        'data': picdata
    }
    if pictags:
        tparams['tags'] = pictags
    if flickr:
        tparams['link'] = flickr
    client.post('post', blog_url=blog, params=tparams)

def twitter_post(pic, caption, tags):
    tagList = tags.split(',')
    tag = random.choice(tagList[:4])
    caption = caption.replace("\\", "").strip(">").strip("`") + " #" + tag
    logger.info("Posting to twitter: " + caption)
    tw.update_with_media(pic, status=caption)
    
    
def main():
    logger.info("Global random language: "+langs[rand_lang])
    # If we don't have photos, get some photos
    if not get_photo_list():
        get_photo_archive()
    # Pick a video with subtitles to gather random text from
    yt_links = get_videos()
    subs = get_subs(yt_links)
    # Time to pick our text from the subs and
    # make sure the translated string is long enough
    try:
        final_quote = sub_translate(subs)
    except:
        final_quote = quote_fallback(subs)
    # Pick a random photo and make sure it is one we haven't used before
    rand_pic, url, width, height = get_photo()
    newphoto = False
    while not newphoto:
        if not get_photo_list():
            get_photo_archive()
        elif rand_pic in photolist:
            cur.execute('DELETE FROM Photos WHERE photo_id=?', (rand_pic,))
            con.commit()
            rand_pic, url, width, height = get_photo()
        else:
            newphoto = True
    # Download and add text to photo
    urllib.request.urlretrieve(url, rand_pic+'.jpg')
    create_image(final_quote, rand_pic+'.jpg', width, height)
    # Build info for tumblr
    cur.execute('SELECT * FROM Photos WHERE photo_id=?', (rand_pic,))
    photo = cur.fetchone()[1:]
    # Make some tags! Gotta promote through randomness!
    tags = flickr_tags(photo)
    caption, link = build_caption(photo, final_quote, ptype="quote")
    tumblr_post('final.jpg', caption, pictags=tags, flickr=link)
    twitter_post('final.jpg', caption, tags)
    # Clean up after myself
    clear_photo(rand_pic)
    cleanup()


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception("An error occurred.")
        cleanup()
