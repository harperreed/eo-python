import datetime
import logging
import random
import sched
import time


class Scheduler(object):
    """The Scheduler will execute a given function at preset times each day, with each time
    jittered by +/- a given number of minutes.

    The jitter feature allows the scheduler to run network access functions in a well-behaved way.
    By slightly varying the scheduled times of functions that access external servers, we reduce
    the probability that many clients will simultaneously make requests to the servers, overloading
    them and leading to dropped requests.
    """

    def __init__(self, schedule, scheduled_fn, scheduled_fn_args=(), schedule_jitter=2):
        """Initialize the scheduler object.

        Args:
            schedule: a list of times at which to run the function.
            scheduled_fn: the function to run at the given times.
            scheduled_fn_args: args to be passed into the scheduled_fn, contained in a sequence.
                For example,
                    scheduler = Scheduler(SCHEDULE, new_favorite, (eo,), SCHEDULE_JITTER)
                Note that this syntax also works:
                    scheduler = Scheduler(SCHEDULE, lambda: new_favorite(eo), schedule_jitter=SCHEDULE_JITTER)
            schedule_jitter: the +/- number of minutes to randomize the scheduled times.
        """
        self.logger = logging.getLogger(".".join(["eo", self.__class__.__name__]))
        self.scheduled_fn = scheduled_fn
        self.scheduled_fn_args = scheduled_fn_args
        self.jitter = schedule_jitter

        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.ingest_schedule(schedule)

    def ingest_schedule(self, schedule):
        """Validate the schedule and store the events as time objects.
        Args:
            schedule: an array of strings of the form "HH:SS". These are the times, in 24 hour time
            format, when the scheduler will call self.scheduled_fn.
        """
        self.schedule = []
        for t in schedule:
            try:
                (h, m) = map(int, t.split(":"))
                if h < 0 or h > 23 or m < 0 or m > 59:
                    raise ValueError('invalid time in schedule: {0}. Skipping.'.format(t))
                self.schedule.append(datetime.time(h, m))
            except Exception as e:
                self.logger.error(e)
        self.schedule.sort()

    def next_event_after(self, day, last_time):
        """Return the next time in the schedule on the given day that is later than last_time.
        Args:
            day: the day to use for the scheduled times
            last_time: the time to exceed
        Return the next time as an combined date & time.
        """
        for t in self.schedule:
            next_time = datetime.datetime.combine(day, t)
            if next_time > last_time:
                return next_time
        return None

    def next_event(self, last_time):
        """Return the next time in the schedule after last_time, possibly tomorrow."""
        today = datetime.date.today()
        next_event = self.next_event_after(today, last_time)
        if not next_event:
            tomorrow = today + datetime.timedelta(days=1)
            first_time = self.schedule[0]
            next_event = datetime.datetime.combine(tomorrow, first_time)
        return next_event

    def add_jitter(self, atime):
        """Add or subtract a random number of minutes to the given time, where the range of time is
        +/- self.jitter. Return the jittered time.
        """
        offset = self.jitter * (2.0 * random.random() - 1.0)
        return atime + datetime.timedelta(minutes=offset)

    def run(self):
        if not self.schedule:
            self.logger.error("No valid schedule to run. Returning.")
            return

        last_time = datetime.datetime.now()
        while True:
            next_time = self.next_event(last_time)
            last_time = next_time  # save before adding jitter
            next_time_time = self.add_jitter(next_time)  # Note: could move into the past.

            self.logger.info("Next update: %s", next_time_time.strftime("%Y-%m-%d %H:%M:%S"))
            next_t = time.mktime(next_time_time.timetuple())
            self.scheduler.enterabs(next_t, 1, self.scheduled_fn, self.scheduled_fn_args)
            self.scheduler.run()
