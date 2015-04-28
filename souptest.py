import urllib.request, urllib.error, urllib.parse
import random, shlex, os, pysrt, goslate, flickrapi
from bs4 import BeautifulSoup
from subprocess import call
from configobj import ConfigObj as configobj

config = configobj('api.conf')

with open('wordlist.txt') as words:
	wordlist = words.read().splitlines()
	
with open('languages.txt') as langlist:
	langsplit = langlist.read().splitlines()
langs = {}
for each in langsplit:
	code = each.split(',')
	langs[code[1]] = code[0]
langs.pop('en')
	
rand_lang = random.choice(list(langs.keys()))
gs = goslate.Goslate()
with open('photos.txt') as old:
	old_photos = old.read().splitlines()
	
photolist = {}
for each in old_photos:
	if each != '':
		photolist[each] = 1
		
if not os.path.exists('photos'):
    os.makedirs('photos')
		
def get_photo(photodir):
	rand_pic = random.choice(photodir)
	archive = os.path.join('photos', rand_pic)
	with open(archive) as pic:
		url,source = pic.read().splitlines()
	return rand_pic, archive, url, source
	

def get_videos():
	rand_word = random.choice(wordlist)
	results = urllib.request.urlopen('https://www.youtube.com/results?search_query='+rand_word).read()
	soup = BeautifulSoup(results)
	yt_links = {}
	for link in soup.find_all('a'):
		x = link.get('href')
		if x.startswith('/watch?') and x not in yt_links:
			yt_links[x] = 'https://www.youtube.com'+x
	return yt_links

def get_photo_archive():
	fconf = config['flickr']
	apikey = fconf['apikey']
	apisecret = fconf['apisecret']
	flickr = flickrapi.FlickrAPI(apikey, apisecret)
	for each in range(1,30):
		rand_word = random.choice(wordlist)	
		photos = flickr.photos.search(text=rand_word, extras='url_l,url_o,path_alias', license='2,4,7,9,10', safesearch='1')
		for pic in photos[0]:
			pic_id= pic.get('id')
			owner = pic.get('pathalias')
			if not pic.get('url_l'):
				url = pic.get('url_o')
			else:
				url = pic.get('url_l')
			source = ('https://www.flickr.com/photos/%s/%s' % (owner, pic_id))
			with open('photos/'+pic_id, 'a') as myFile:
				myFile.write(url+'\n')
				myFile.write(source)
			print(url)
			print(source)

if os.listdir('photos') == []:
	get_photo_archive()
	
yt_links = get_videos()
has_subtitles = False
while not has_subtitles:
	if yt_links != {}:
		chosen_key = random.choice(list(yt_links.keys()))
		chosen_one = yt_links[chosen_key]
		print("CHOSEN!", chosen_one)
		command = ('youtube-dl --no-playlist --write-sub --write-auto-sub --sub-lang "en" --skip-download "%s" --restrict-filenames' % (chosen_one,))
		call(shlex.split(command))
		contents = os.listdir('.')
		print("DEBUG", contents)
		for each in contents:
			if each.endswith('.srt'):
				subs = pysrt.open(each)
				has_subtitles = True
		if not has_subtitles:
			yt_links.pop(chosen_key)
	else:
		yt_links = get_videos()
	
long_enough = False
while not long_enough:
	rand_section = random.choice(subs)
	rand_quote = rand_section.text
	print('DEBUG rand_quote first-', rand_quote)
	translation = gs.translate(rand_quote, rand_lang).encode('utf-8')
	print('DEBUG translation-', translation)
	print('DEBUG rand_lang-', rand_lang)
	retranslate = gs.translate(translation, 'en')
	print('DEBUG retranslate-', retranslate)
	if (len(retranslate.split()) > 6) and (len(retranslate.split()) < 15):
		long_enough = True

print('DEBUG rand_quote final-', rand_quote)
transfer_quote = retranslate.replace('\n', '--!--')

banned_tags = {'is':1, 'are':1, 'do':1, 'the':1, 'an':1, 'of':1, 'at':1, 'on':1, 'i':1, 'me':1, 'you':1, 'a':1, 'to':1, 'from':1, 'and':1, 'or':1, 'but':1, 'we':1, 'us':1, 'in':1, 'he':1, 'she':1, 'they':1, 'not':1, 'no':1, 'yes':1}
tags_select = retranslate.strip("',.:!?").split()
tagdict = {}
taglist = []
for i in range(1,20):
	tag = random.choice(tags_select)
	if (tag.lower() not in tagdict) and (tag.lower() not in banned_tags) and (len(taglist) < 4):
		tagdict[tag] = 1
		taglist.append(tag)
print(taglist)
tags = ''
for each in taglist:
	tags = tags + each + ','
tags = tags + langs[rand_lang]
print(tags)


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
		
with open('photos.txt', 'a') as photos:
	photos.write(rand_pic+'\n')
	
with open('translate.out', 'w') as output:
	output.write(url+'\n'+source+'\n'+transfer_quote+'\n'+tags)
	
for each in os.listdir('.'):
	if each.endswith('.srt'):
		cmd = 'rm "'+each+'"'
		call(shlex.split(cmd))
		
