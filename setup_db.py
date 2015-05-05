#!/usr/bin/python3
import os, souptest, flickerapi
import sqlite3 as lite
from configobj import ConfigObj as configobj
config = configobj('api.conf')

fconf = config['flickr']
apikey = fconf['apikey']
apisecret = fconf['apisecret']
flickr = flickrapi.FlickrAPI(apikey, apisecret)
licenses = flickr.photos.licenses.getInfo()
lic_dict = {}

con = lite.connect('soup.sqlite')
cur = con.cursor()

def print_db(db):
	cur.execute('SELECT * FROM ?', db)
	data = cur.fetchall()
	for each in data:
		print(each)
	
cur.execute('CREATE TABLE IF NOT EXISTS Photos(Id INTEGER PRIMARY KEY, photo_id INTEGER, user TEXT, url TEXT, width INTEGER, height INTEGER, title TEXT, owner TEXT, license INTEGER)')
cur.execute('CREATE TABLE IF NOT EXISTS Hold(Id INTEGER PRIMARY KEY, photo_id INTEGER, user TEXT, url TEXT, width INTEGER, height INTEGER, title TEXT, owner TEXT, license INTEGER)')
cur.execute('CREATE TABLE IF NOT EXISTS Licenses(Id INTEGER PRIMARY KEY, lic_id INTEGER, name TEXT, url TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS Bantags(Id INTEGER PRIMARY KEY, tag TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS Banusers(Id INTEGER PRIMARY KEY, user TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS Languages(Id INTEGER PRIMARY KEY, code TEXT, language TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS Words(Id INTEGER PRIMARY KEY, word TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS old_photos(Id INTEGER PRIMARY KEY, photo INTEGER)')

for each in licenses[0]:
	licid = int(each.get('id'))
	if licid == 2:
		name = 'CC BY-NC'
		cur.execute('INSERT INTO Licenses(lic_id, name, url) VALUES(?,?,?)', (licid, name, each.get('url')))
	elif licid == 4:
		name = 'CC BY'
		cur.execute('INSERT INTO Licenses(lic_id, name, url) VALUES(?,?,?)', (licid, name, each.get('url')))
	elif licid == 7:
		name = "NONE"
		cur.execute('INSERT INTO Licenses(lic_id, name, url) VALUES(?,?,?)', (licid, name, each.get('url')))
print_db('Licenses')
	
with open(os.path.join('database','bantags.txt'), 'r') as bantags:
	banlist = bantags.read().splitlines()	
for each in banlist:
	cur.execute('INSERT INTO Bantags(tag) VALUES(?)', (each,))
print_db('Bantags')
	
with open(os.path.join('database','languages.txt'), 'r') as langs:
	langlist = langs.read().splitlines()	
for each in langlist:
	language, code = each.split(',')
	cur.execute('INSERT INTO Languages(code,language) VALUES(?,?)', (code, language))
print_db('Languages')
	
with open(os.path.join('database','wordlist.txt'), 'r') as words:
	wordlist = words.read().splitlines()	
for each in wordlist:
	cur.execute('INSERT INTO Words(word) VALUES(?)', (each,))
print_db('Words')
	
con.commit()
