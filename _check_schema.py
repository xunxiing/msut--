import sqlite3
c = sqlite3.connect("server/data/data.sqlite")
print(c.execute("SELECT sql FROM sqlite_master WHERE name='resources'").fetchone()[0])
print("---")
for row in c.execute("SELECT id, title, description FROM resources LIMIT 5"):
    print(row)
