#!/usr/bin/python2
import pytumblr, os.path, shlex
import sqlite3 as lite
from configobj import ConfigObj as configobj
from subprocess import call
tconf = configobj('api.conf')['tumblr']
consumer_key = tconf['consumer_key']
consumer_secret = tconf['consumer_secret']
oauth_token = tconf['oauth_token']
oauth_secret = tconf['oauth_secret']
blog_host = tconf['blog_host']

client = pytumblr.TumblrRestClient(
	consumer_key, 
	consumer_secret, 
	oauth_token, 
	oauth_secret
)

con = lite.connect('soup.sqlite')
cur = con.cursor()

def post_it(flickr,quote,trans_tags):
	trans_tags = trans_tags.split(',')
	client.create_photo(blog_host, state="queue", tags=trans_tags, format='markdown', link=flickr, data="final.jpg", caption=quote)
	
def build_attrib(photo, quote):
	photo_id, user, pic_url, width, height, title, owner, license = photo
	cur.execute('SELECT * FROM Licenses WHERE lic_id=?', (license,))
	lic,lic_url = cur.fetchone()[2:]
	profile = 'https://www.flickr.com/photos/'+user
	flickr = 'https://www.flickr.com/'+user+'/'+str(photo_id)
	if lic == 'NONE':
		caption = """>`%s`

Photo: [%s](%s) from [%s](%s)""" % (quote,title,flickr,owner,profile)
	else:
		caption = """>`%s`

Photo: [%s](%s) by [%s](%s) licensed under [%s](%s)""" % (quote,title,flickr,owner,profile,lic,lic_url)
	return caption, flickr
	
if os.path.isfile('translate.out'):
	cur.execute('SELECT * FROM Hold')
	photo = cur.fetchone()[1:]
	with open('translate.out') as output:
		quote, trans_tags = output.read().splitlines()
	caption, url = build_attrib(photo, quote)
	post_it(url,caption,trans_tags)
	call(shlex.split('rm translate.out'))
