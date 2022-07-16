from index import cursor_n, mydb_n


def afkState(user: int):
    cursor_n.execute(f"SELECT * FROM public.afk WHERE guild = '{user}'")
    row = cursor_n.fetchall()

    if len(row) == 0:
        return

    afkBool = bool

    afkBool = row[0][1] == True
    mydb_n.commit()
    return afkBool


def afkNotes(user: int):
    cursor_n.execute(f"SELECT * FROM public.afk WHERE user = '{user}'")
    row = cursor_n.fetchall()

    if len(row) == 0:
        return

    afkStr = str

    afkStr = str(row[0][2]) if row[0][1] == True else "Not AFK"
    mydb_n.commit()
    return afkStr


afks = {}
