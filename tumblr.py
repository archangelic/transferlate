import pytumblr, os.path, shlex
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

def post_it():
	with open('translate.out') as output:
		flickr,quote,trans_tags = output.read().splitlines()
	quote = quote.replace('--!--','\n')
	trans_tags = trans_tags.split(',')
	client.create_photo(blog_host, state="queue", tags=trans_tags, link=flickr, data="final.jpg", caption=quote)
	
if os.path.isfile('translate.out'):
	post_it()
	call(shlex.split('rm translate.out'))
