### IMPORTANT ANNOUNCEMENT ###
#
# All additions to AGB will now cease.
# AGB's management will be limited to the following:
# - Optimization
# - Bug Fixes
# - Basic Maintenance
#
# DO NOT ADD ANY NEW FEATURES TO AGB
# ALL NEW FEATURES WILL BE RESERVED FOR MEKU
#
### IMPORTANT ANNOUNCEMENT ###

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
                f"ALTER TABLE public.commands ADD COLUMN {name.lower()} VARCHAR(75);"
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
            f"ALTER TABLE public.commands ADD COLUMN {name.lower()} VARCHAR(75);"
        )
        mydb_n.commit()
        return False

    return cmdBool


commandsEnabled = {}
