#!/usr/bin/env python3
import os
import flickrapi
import sqlite3 as lite
from configobj import ConfigObj
config = ConfigObj('api.conf')

con = lite.connect('soup.db')
cur = con.cursor()

cur.execute(('CREATE TABLE IF NOT EXISTS Photos'
             '(Id INTEGER PRIMARY KEY, photo_id INTEGER, user TEXT, url TEXT,'
             ' width INTEGER, height INTEGER, title TEXT, owner TEXT,'
             ' license INTEGER)'))
cur.execute(('CREATE TABLE IF NOT EXISTS Licenses'
             '(Id INTEGER PRIMARY KEY, lic_id INTEGER, name TEXT, url TEXT)'))
cur.execute(('CREATE TABLE IF NOT EXISTS Languages'
             '(Id INTEGER PRIMARY KEY, code TEXT, language TEXT)'))
cur.execute(('CREATE TABLE IF NOT EXISTS Words'
             '(Id INTEGER PRIMARY KEY, word TEXT)'))
cur.execute(("CREATE TABLE IF NOT EXISTS old_photos"
             "(Id INTEGER PRIMARY KEY, photo INTEGER)"))

with open(os.path.join('database', 'languages.txt'), 'r') as langs:
    langlist = langs.read().splitlines()
for each in langlist:
    language, code = each.split(',')
    cur.execute('INSERT INTO Languages(code,language) VALUES(?,?)',
                (code, language))
cur.execute("SELECT * FROM Languages")
data = cur.fetchall()
for each in data:
    print(each)

with open(os.path.join('database', 'wordlist.txt'), 'r') as words:
    wordlist = words.read().splitlines()
for each in wordlist:
    cur.execute('INSERT INTO Words(word) VALUES(?)', (each,))
cur.execute("SELECT * FROM Words")
data = cur.fetchall()
for each in data:
    print(each)

con.commit()
