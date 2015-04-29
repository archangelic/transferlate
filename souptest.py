import urllib.request, urllib.error, urllib.parse
import random, shlex, os, pysrt, goslate, flickrapi
from bs4 import BeautifulSoup
from subprocess import call
from configobj import ConfigObj as configobj

config = configobj('api.conf')
gs = goslate.Goslate()
# Get list of words for random queries
with open('wordlist.txt') as words:
	wordlist = words.read().splitlines()
# Build list of languages accepted by goslate
with open('languages.txt') as langlist:
	langsplit = langlist.read().splitlines()
langs = {}
for each in langsplit:
	code = each.split(',')
	langs[code[1]] = code[0]
langs.pop('en')
rand_lang = random.choice(list(langs.keys()))
# Build a list of photos we have already used
with open('photos.txt') as old:
	old_photos = old.read().splitlines()
photolist = {}
for each in old_photos:
	if each != '':
		photolist[each] = 1
# Gotta have a place to store photos
if not os.path.exists('photos'):
    os.makedirs('photos')
# List of words that don't make for good tags
banned_tags = {'is':1, 'are':1, 'do':1, 'the':1, 'an':1, 
			   'of':1, 'at':1, 'on':1, 'i':1, 'me':1, 
			   'you':1, 'a':1, 'to':1, 'from':1, 'and':1,
			   'or':1, 'but':1, 'we':1, 'us':1, 'in':1,
			   'he':1, 'she':1, 'they':1, 'not':1, 'no':1,
			   'yes':1, 'it':1, 'be':1, 'was':1, 'as':1,
			   'this':1, 'with':1, 'like':1, 'there':1, 'for':1,
			   'her':1, 'him':1, 'them':1}
		
def get_photo(photodir): # Picks a random photo and grabs data to give to the script
	rand_pic = random.choice(photodir)
	archive = os.path.join('photos', rand_pic)
	with open(archive) as pic:
		url,source = pic.read().splitlines()
	return rand_pic, archive, url, source

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
	for each in range(1,30):
		rand_word = random.choice(wordlist)	
		photos = flickr.photos.search(text=rand_word, extras='url_l,url_o,path_alias', license='2,4,7,9,10', safesearch='1', tags='landscape,nature,space', content_type='1')
		for pic in photos[0]:
			if pic.get('pathalias'):
				pic_id= pic.get('id')
				owner = pic.get('pathalias')
				if not pic.get('url_l'):
					url = pic.get('url_o')+','+pic.get('width_o')+','+pic.get('height_o')
				else:
					url = pic.get('url_l')+','+pic.get('width_l')+','+pic.get('height_l')
				source = ('https://www.flickr.com/photos/%s/%s' % (owner, pic_id))
				with open('photos/'+pic_id, 'a') as myFile:
					myFile.write(url+'\n')
					myFile.write(source)
					
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

# If we don't have photos, get some photos
if not os.listdir('photos'):
	get_photo_archive()
# Pick a video with subtitles to gather random text from
yt_links = get_videos()
subs = get_subs(yt_links)
# Time to pick our text from the subs and make sure the translated string is long enough
long_enough = False
x = 0
while not long_enough:
	if x == 10:
		yt_links = get_videos()
		subs = get_subs(yt_links)
		x = 0
	rand_section = random.choice(subs)
	rand_quote = rand_section.text
	translation = gs.translate(rand_quote, rand_lang).encode('utf-8')
	retranslate = gs.translate(translation, 'en')
	if (len(retranslate.split()) > 6) and (len(retranslate.split()) < 15):
		long_enough = True
	x += 1
# Prepare a version of the quote to be passed to tumblr.py
transfer_quote = retranslate.replace('\n', '--!--')
# Make some tags! Gotta promote through randomness!
tags_split = retranslate.split()
tags_select = []
for each in tags_split:
	i = each.strip().strip("!@#$%^&*()-_=+,<.>/?;:'[]{}`~").lower()
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
rand_pic, archive, url, source = get_photo(os.listdir('photos'))
newphoto = False
while not newphoto:
	if os.listdir('photos') == []:
		get_photo_archive()
	elif (rand_pic in photolist):
		cmd = 'rm '+archive
		call(shlex(cmd))
		rand_pic, archive, url, source = get_photo(os.listdir('photos'))
	else:
		newphoto = True
url, width, height = url.split(',')
# Download and add text to photo
urllib.request.urlretrieve(url, rand_pic+'.jpg')
width = str(int(width)-100)
height = str(int(height)-100)
cmd = '''convert -background none -gravity center -font Helvetica -fill white -stroke black -strokewidth 2 -size %sx%s\
	caption:"%s"\
	%s.jpg +swap -gravity center -composite final.jpg''' % (width, height, retranslate, rand_pic)
call(shlex.split(cmd))
# Add photo to list of used photos
with open('photos.txt', 'a') as photos:
	photos.write(rand_pic+'\n')
# Create file to pass info to tumblr.py
with open('translate.out', 'w') as output:
	output.write(source+'\n'+transfer_quote+'\n'+tags)
# Clean up after myself
for each in os.listdir('.'):
	if each.endswith('.srt'):
		cmd = 'rm "'+each+'"'
		call(shlex.split(cmd))
	if each.endswith('.jpg') and (each != 'final.jpg'):
		cmd = 'rm "'+each+'"'
		call(shlex.split(cmd))
		
