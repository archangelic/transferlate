#!/usr/bin/python3
import urllib.request, urllib.error, urllib.parse
import random, shlex, os, pysrt, goslate, flickrapi
import sqlite3 as lite
from bs4 import BeautifulSoup
from subprocess import call
from configobj import ConfigObj as configobj

config = configobj('api.conf')
gs = goslate.Goslate()
con = lite.connect('soup.sqlite')
cur = con.cursor()
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
# Clear out the holding table
cur.execute('DELETE FROM Hold')
con.commit()
	
def get_photo_list():
	cur.execute('SELECT * FROM Photos')
	photos = cur.fetchall()
	photo_archive = {}
	for each in photos:
		db_id, photo_id, user, url, width, height, title, owner, lic = each
		photo_archive[photo_id] = (url, width, height)
	return photo_archive

def get_photo(): # Picks a random photo and grabs data to give to the script.
	photos = get_photo_list()
	rand_pic = random.choice(list(photos.keys()))
	url, width, height = photos[rand_pic]
	return str(rand_pic), url, width, height

def get_videos(): # Gets videos by scraping the youtube search page for links
	rand_word = random.choice(wordlist)
	results = urllib.request.urlopen('https://www.youtube.com/results?search_query='+rand_word).read()
	soup = BeautifulSoup(results)
	yt_links = {}
	for link in soup.find_all('a'):
		x = link.get('href')
		if x.startswith('/watch?') and x not in yt_links:
			yt_links[x] = 'https://www.youtube.com'+x
	return yt_links

def get_photo_archive(): # Builds the photo archive
	fconf = config['flickr']
	apikey = fconf['apikey']
	apisecret = fconf['apisecret']
	flickr = flickrapi.FlickrAPI(apikey, apisecret)
	tagchoices = ['landscape', 'nature']
	for each in range(1,30):
		rand_word = random.choice(wordlist)	
		photos = flickr.photos.search(text=rand_word, extras='url_l,url_o,path_alias,owner_name,license', license='2,4,7', safesearch='1', tags=random.choice(tagchoices), tag_mode='all', content_type='1')
		for pic in photos[0]:
			cur.execute('SELECT EXISTS(SELECT * FROM Photos WHERE photo_id=?)', (pic.get('id'),))
			pic_check = cur.fetchall()[0][0]
			if pic.get('pathalias') and (pic_check == 0):
				title = pic.get('title')
				pic_id= pic.get('id')
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
				license = int(pic.get('license'))
				cur.execute('INSERT INTO Photos(photo_id, user, url, width, height, title, owner, license) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', (pic_id, user, url, width, height, title, owner, license))
				con.commit()
					
def get_subs(yt_links):
	has_subtitles = False
	while not has_subtitles:
		if yt_links != {}:
			chosen_key = random.choice(list(yt_links.keys()))
			chosen_one = yt_links[chosen_key]
			command = ('/usr/local/bin/youtube-dl -q --no-warnings --no-playlist --write-sub --write-auto-sub --sub-lang "en" --skip-download "%s" --restrict-filenames' % (chosen_one,))
			call(shlex.split(command))
			contents = os.listdir('.')
			for each in contents:
				if each.endswith('.srt'):
					subs = pysrt.open(each)
					has_subtitles = True
			if not has_subtitles:
				yt_links.pop(chosen_key)
		else:
			yt_links = get_videos()
	return subs

def cleanup():
	for each in os.listdir('.'):
		if each.endswith('.srt'):
			cmd = 'rm "'+each+'"'
			call(shlex.split(cmd))
		if each.endswith('.jpg') and (each != 'final.jpg'):
			cmd = 'rm "'+each+'"'
			call(shlex.split(cmd))

def clean_quote(text):
	text_trails = True
	while text_trails:
		text = text.strip().strip("@#$%^&*()-_=+,<>/;:'[]{}`~")
		if text.strip('.?!').endswith((' and', ' an', ' the', ' but', ' or', ' nor', ' a')):
			trail_len = len(text.split()[-1])
			text = text[:-trail_len]
		else:
			text_trails = False
	text = text[0].upper()+text[1:]
	if not text.endswith(('.','!','?')):
		text += '.'
	return text

def hold_info(pic_id):
	cur.execute('SELECT * FROM Photos WHERE photo_id=?', (pic_id,))
	photo = cur.fetchone()[1:]
	cur.execute('INSERT INTO Hold(photo_id, user, url, width, height, title, owner, license) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', (photo))
	con.commit()
	cur.execute('DELETE FROM Photos WHERE photo_id=?', (pic_id,))
	con.commit()

if __name__ == '__main__':
	# If we don't have photos, get some photos
	if not get_photo_list():
		get_photo_archive()
	# Pick a video with subtitles to gather random text from
	yt_links = get_videos()
	subs = get_subs(yt_links)
	# Time to pick our text from the subs and make sure the translated string is long enough
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
		translation = gs.translate(rand_quote, rand_lang).encode('utf-8')
		retranslate = gs.translate(translation, 'en')
		final_quote = clean_quote(retranslate)
		if (len(final_quote.split()) > 6) and (len(final_quote.split()) < 15):
			long_enough = True
		x += 1
	# Make some tags! Gotta promote through randomness!
	tags_split = final_quote.split()
	tags_select = []
	for each in tags_split:
		i = each.strip().strip(".!?@#$%^&*()-_=+,<>/;:'[]{}`~").lower()
		if i:
			tags_select.append(i)
	tagdict = {}
	taglist = []
	for i in range(1,100):
		tag = random.choice(tags_select)
		if (tag not in tagdict) and (tag not in banned_tags) and (len(taglist) < 4):
			tagdict[tag] = 1
			taglist.append(tag)
	tags = ''
	for each in taglist:
		tags = tags + each + ','
	tags = tags + langs[rand_lang]
	# Pick a random photo and make sure it is one we haven't used before
	rand_pic, url, width, height = get_photo()
	newphoto = False
	while not newphoto:
		if not get_photo_list():
			get_photo_archive()
		elif (rand_pic in photolist):
			cur.execute('DELETE FROM Photos WHERE photo_id=?', (rand_pic,))
			con.commit()
			rand_pic, url, width, height = get_photo()
		else:
			newphoto = True
	# Download and add text to photo
	urllib.request.urlretrieve(url, rand_pic+'.jpg')
	width = str(int(width)-100)
	height = str(int(height)-100)
	cmd = '''convert -background none -gravity center -font Helvetica -fill white -stroke black -strokewidth 2 -size %sx%s\
		caption:"%s"\
		%s.jpg +swap -gravity center -composite final.jpg''' % (width, height, final_quote, rand_pic)
	call(shlex.split(cmd))
	# Create file to pass info to tumblr.py
	hold_info(rand_pic)
	with open('translate.out', 'w') as output:
		output.write(final_quote+'\n'+tags)
	# Clean up after myself
	cleanup()
