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

"""Collection of classes to store the states of a specific discord guild bot."""


class Guilds:
    """Class that stores all the 'Guild' classes."""

    def __init__(self):
        self.guilds = {}

    def __call__(self, ctx):
        """Allows the instance of this class to be called and return a guild."""

        id = ctx.guild.id  # get the id of the guild of the given context
        guild = self.guilds.get(id)  # get the 'Guild' object of a given id

        # check if the guild is already stored then return it
        if guild:
            return guild
        # if not, then create a new 'Guild' object and store it then return it
        else:
            guild = Guild(id)
            self.guilds[id] = guild
            return guild


class Guild:
    """Stores some states of a specific discord guild bot."""

    def __init__(self, id):
        self.queue = Queue()
        self.has_played_voice = False


class Queue:
    """Stores objects in queue like data structure."""

    def __init__(self):
        self.queue = []

    def __getitem__(self, index):
        """Allows indexing to the object itself to get an item in the queue."""
        return self.queue[index]

    @property
    def current(self):
        """Get and return the first item in queue."""
        try:
            return self[0]
        except IndexError:
            return None

    def pop(self, index):
        """Remove an item in queue by index."""
        return self.queue.pop(index)

    def clear(self):
        """Reset the queue."""
        self.queue.clear()

    def enqueue(self, obj):
        """Enqueue an item in the right side of the queue."""
        self.queue.append(obj)

    def dequeue(self):
        """Dequeue an item in the left side of the queue."""
        return self.pop(0)

    def shift(self, n):
        """Shift the queue by 'n' times."""
        self.queue = self.queue[n:] + self.queue[:n]
