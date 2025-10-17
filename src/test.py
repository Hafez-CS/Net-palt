import sqlite3

db = sqlite3.connect("chat_app.db")

cur = db.cursor()

res = cur.execute("SELECT * FROM users").fetchall()
for i in  res:
    print(i)