
import datetime


def log(msg):
    """Simple logger: print with a timestamp."""
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H:%M:%S")
    print "{0}: {1}".format(timestamp, msg)
