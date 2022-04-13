import psycopg

from index import cursor_n, mydb_n


def cmd(name: str, guild: int):
    cmdBool = bool
    try:
        cursor_n.execute(
            f"SELECT {name.lower()} FROM public.commands WHERE guild = '{guild}'"
        )

        cmdRow = cursor_n.fetchall()
        rowCount = cursor_n.rowcount

        if rowCount == 0:
            cursor_n.execute(
                f"ALTER TABLE public.commands ADD COLUMN IF NOT EXISTS {name.lower()} VARCHAR(75);"
            )
            mydb_n.commit()
            return False
        else:
            if cmdRow[0][0] == "true":
                cmdBool = True
            else:
                cmdBool = False
            mydb_n.commit()
    except psycopg.errors.UndefinedColumn:
        cursor_n.execute(
            f"ALTER TABLE public.commands ADD COLUMN IF NOT EXISTS {name.lower()} VARCHAR(75);"
        )
        mydb_n.commit()
        return False

    return cmdBool


commandsEnabled = {}
