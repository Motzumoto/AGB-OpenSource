from index import cursor_n, mydb_n


def afkState(user: int):
    cursor_n.execute(f"SELECT * FROM public.afk WHERE guild = '{user}'")
    row = cursor_n.fetchall()

    if len(row) == 0:
        return

    afkBool = bool

    if row[0][1] == True:
        afkBool = True
    else:
        afkBool = False

    mydb_n.commit()
    return afkBool


def afkNotes(user: int):
    cursor_n.execute(f"SELECT * FROM public.afk WHERE user = '{user}'")
    row = cursor_n.fetchall()

    if len(row) == 0:
        return

    afkStr = str

    if row[0][1] == True:
        afkStr = str(row[0][2])
    else:
        afkStr = "Not AFK"

    mydb_n.commit()
    return afkStr


afks = {}
