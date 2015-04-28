import pytumblr
from configobj import ConfigObj as configobj
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

with open('translate.out') as output:
	url,flickr,quote,trans_tags = output.read().splitlines()

quote = quote.replace('--!--','\n')
trans_tags = trans_tags.split(',')
	
client.create_photo(blog_host, state="published", tags=trans_tags, source=url, link=flickr, caption=quote)