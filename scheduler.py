import logging
import time


class Scheduler(object):

    def __init__(self, schedule, scheduled_fn, schedule_jitter=2):
        """
        Args:
            schedule: a list of times at which to run the function.
            scheduled_fn: the function to run at the given times.
            schedule_jitter: the +/- number of minutes to randomize the scheduled times.
        """
        self.logger = logging.getLogger('.'.join([__name__, self.__class__.__name__]))
        self.scheduled_fn = scheduled_fn

    def run(self):
        self.logger.info("Now running the schedule.")
        while True:
            self.scheduled_fn()
            self.logger.info("sleeping.")
            time.sleep(20)
