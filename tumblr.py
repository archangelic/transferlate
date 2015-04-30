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

def post_it(flickr,quote,trans_tags):
	quote = quote.replace('--!--','\n')
	trans_tags = trans_tags.split(',')
	client.create_photo(blog_host, state="queue", tags=trans_tags, format='markdown', link=flickr, data="final.jpg", caption=quote)
	
def build_attrib(flickr,quote,title,attrib):
	if attrib.split(',')[0] == 'NONE':
		owner,profile = attrib.split(',')[1:]
		caption = """>`%s`

Photo: [%s](%s) from [%s](%s)""" % (quote,title,flickr,owner,profile)
	else:
		owner,profile,lic,lic_url = attrib.split(',')
		caption = """>`%s`

Photo: [%s](%s) by [%s](%s) licensed under [%s](%s)""" % (quote,title,flickr,owner,profile,lic,lic_url)
	return caption
	
if os.path.isfile('translate.out'):
	with open('translate.out') as output:
		flickr,quote,trans_tags,title,attrib = output.read().splitlines()
	caption = build_attrib(flickr,quote,title,attrib)
	post_it(flickr,caption,trans_tags)
	call(shlex.split('rm translate.out'))
