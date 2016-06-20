#!/usr/bin/env python3
import os
import sqlite3 as lite


def build_database():
    con = lite.connect('soup.db')
    cur = con.cursor()

    cur.execute(('CREATE TABLE IF NOT EXISTS Photos'
                 '(Id INTEGER PRIMARY KEY, photo_id INTEGER, user TEXT, url TEXT,'
                 ' width INTEGER, height INTEGER, tags TEXT'))
    cur.execute(('CREATE TABLE IF NOT EXISTS Words'
                 '(Id INTEGER PRIMARY KEY, word TEXT)'))
    cur.execute(("CREATE TABLE IF NOT EXISTS old_photos"
                 "(Id INTEGER PRIMARY KEY, photo INTEGER)"))

    with open(os.path.join('database', 'wordlist.txt'), 'r') as words:
        wordlist = words.read().splitlines()
    for each in wordlist:
        cur.execute('INSERT INTO Words(word) VALUES(?)', (each,))

    con.commit()


def migrate():
    os.rename("soup.db", "backup.db")
    build_database()
    bk = lite.connect('backup.db')
    sp = lite.connect('soup.db')
    bcur = bk.cursor()
    scur = sp.cursor()
    bcur.execute("SELECT photo_id, user, url, width, height, tags FROM Photos")
    photos = bcur.fetchall()
    for each in photos:
        # scur.execute('INSERT INTO Photos(photo_id, user, url, width, height, tags) VALUES(?, ?, ?, ?, ?, ?)',
                    #  tuple(each))
        print(each)


if __name__ == "__main__":
    build_database()
