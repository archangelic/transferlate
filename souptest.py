#!/usr/bin/python3
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
banned_tags = {}
with open('banned.txt') as banned:
	banned_list = banned.read().splitlines()
for each in banned_list:
	if each:
		banned_tags[each] = 1
		
def get_photo(photodir): # Picks a random photo and grabs data to give to the script
	rand_pic = random.choice(photodir)
	archive = os.path.join('photos', rand_pic)
	with open(archive) as pic:
		url,source,title,attrib = pic.read().splitlines()
	return rand_pic, archive, url, source, title, attrib

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
	licenses = flickr.photos.licenses.getInfo()
	lic_dict = {}
	tagchoices = ['landscape', 'nature', 'space']
	for each in licenses[0]:
		lic_dict[each.get('id')] = each.get('url')
	for each in range(1,30):
		rand_word = random.choice(wordlist)	
		photos = flickr.photos.search(text=rand_word, extras='url_l,url_o,path_alias,owner_name,license', license='2,4,7', safesearch='1', tags=random.choice(tagchoices), tag_mode='all', content_type='1')
		for pic in photos[0]:
			if pic.get('pathalias'):
				title = pic.get('title')
				pic_id= pic.get('id')
				owner_url = pic.get('pathalias')
				owner = pic.get('ownername')
				if not pic.get('url_l'):
					url = pic.get('url_o')+','+pic.get('width_o')+','+pic.get('height_o')
				else:
					url = pic.get('url_l')+','+pic.get('width_l')+','+pic.get('height_l')
				img_page = ('https://www.flickr.com/photos/%s/%s' % (owner_url, pic_id))
				pic_lic = pic.get('license')
				if pic_lic == '2':
					source = title+'\n'+owner+'--!--'+("https://www.flickr.com/photos/%s" % (owner_url))+'--!--CC BY-NC--!--'+lic_dict[pic_lic]
				elif pic_lic == '4':
					source = title+'\n'+owner+'--!--'+("https://www.flickr.com/photos/%s" % (owner_url))+'--!--CC BY--!--'+lic_dict[pic_lic]
				elif pic_lic == '7':
					source = title+'\n'+'NONE--!--'+owner+'--!--'+("https://www.flickr.com/photos/%s" % (owner_url))
				with open('photos/'+pic_id, 'w') as myFile:
					myFile.write(url+'\n')
					myFile.write(img_page+'\n')
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

if __name__ == '__main__':
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
	rand_pic, archive, url, source, title, attrib = get_photo(os.listdir('photos'))
	newphoto = False
	while not newphoto:
		if os.listdir('photos') == []:
			get_photo_archive()
		elif (rand_pic in photolist):
			cmd = 'rm '+archive
			call(shlex.split(cmd))
			rand_pic, archive, url, source, title, attrib = get_photo(os.listdir('photos'))
		else:
			newphoto = True
	url, width, height = url.split(',')
	# Download and add text to photo
	urllib.request.urlretrieve(url, rand_pic+'.jpg')
	width = str(int(width)-100)
	height = str(int(height)-100)
	cmd = '''convert -background none -gravity center -font Helvetica -fill white -stroke black -strokewidth 2 -size %sx%s\
		caption:"%s"\
		%s.jpg +swap -gravity center -composite final.jpg''' % (width, height, final_quote, rand_pic)
	call(shlex.split(cmd))
	# Add photo to list of used photos
	with open('photos.txt', 'a') as photos:
		photos.write(rand_pic+'\n')
	# Create file to pass info to tumblr.py
	with open('translate.out', 'w') as output:
		output.write(source+'\n'+final_quote+'\n'+tags+'\n'+title+'\n'+attrib)
	# Clean up after myself
	cleanup()
