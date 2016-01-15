from lxml import html
import logging
import random
import requests
import time

# BEST PRACTICE, "rate limiting": don't hit server at maximum rate.
# Minimum time between requests.
MIN_REQUEST_INTERVAL = 0.75  # seconds, float

# BEST PRACTICE, "exponential backoff": If you do retries, back them off
# exponentially. If the server is down or struggling to come back up, you'll
# avoid creating a stampede of clients retrying their requests.
# What's the first retry delay? If more retries are needed, double each delay.
INITIAL_RETRY_DELAY = 4.0  # seconds, float

# BEST PRACTICE, "retry limits": don't keep hitting a downed server.
# In this code, if there's a missed update, we can just wait until the next scheduled update
# to try again. So we don't need to retry many times.
# The number of retry attempts.
NUM_RETRIES = 4

# BEST PRACTICE, "jitter": don't retry or repeat requests at fixed times or
# delays. Vary them slightly to desynchronize clients.
# The amount of variation as a float. 0.20 == +/- 20%
JITTER_FACTOR = 0.20

# Note if a logger is not configured when this class is instantiated, an error will issue like:
#       No handlers could be found for logger "eo.EO_Net"
# To fix, initialize a logger in your main. This class writes error messages to the logging system.


class EO_Net(object):
    """The EO_Net class provides network functions for the API.

    Calls are made against the session stored in self.session.

    Calls are rate limited and include retries with jitter, limits, and exponential backoff.
    """

    def __init__(self):
        self.logger = logging.getLogger(".".join(["eo", self.__class__.__name__]))
        self.session = None
        self.last_request_time = 0

    def get_session(self):
        return self.session

    def set_session(self, session):
        self.session = session

    def request_authenticity_token(self, url):
        """Request, parse, and return the authenticity token needed to post to the given URL."""
        authenticity_token = ""

        # Request the page with the token.
        self.check_request_rate()
        response = self.request_with_retries(url)
        if not response:
            self.logger.error("unable to read {0}.".format(url))
            return ""
        elif response.status_code != requests.codes.ok:
            self.logger.error("unable to read: {0}. Status: {1}, response: {2}".
                              format(url, response.status_code, response.text))
            return ""

        # Parse out the token.
        try:
            tree = html.fromstring(response.content)
            authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
        except Exception as e:
            self.logger.error("problem parsing authenticity token: " + str(e))
        return authenticity_token

    def post_with_authenticity(self, url, payload):
        """Post to the given URL, first obtaining an authenticity token and adding it to the
        payload.

        Return the request result or None.
        """
        authenticity_token = self.request_authenticity_token(url)
        if not authenticity_token:
            return None
        payload["authenticity_token"] = authenticity_token
        return self.post_payload(url, payload)

    def post_payload(self, url, payload):
        """Post the given payload to the given URL

        Args:
            url: the target URL
            payload: the key/values to post.

        Returns:
            The server's response or None.
        """
        self.check_request_rate()
        response = self.request_with_retries(url, method="POST", params=payload)
        if response and response.status_code == requests.codes.ok:
            return response

        if not response:
            self.logger.error("unable to post to {0}.".format(url))
        else:
            self.logger.error("unable to post to {0}. Status: {1}, response: {2}".
                              format(url, response.status_code, response.text))
        return None

    def check_request_rate(self):
        """Are we making requests too fast? If so, pause.

        Specifically, check the current time against the last request time. If
        less than MIN_REQUEST_INTERVAL, sleep the remaining time.

        TODO: This function pauses the whole program. Improvement: create a
        request queue that handles request asynchronously.
        """
        interval = time.clock() - self.last_request_time
        if interval < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - interval)

    def execute_request(self, url, params=None, method="GET"):
        """Request the given URL with the given method and parameters.

        Args:
            url: The URL to call.
            params: The optional parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.

        Returns:
            The server response or None.
        """
        self.check_request_rate()
        try:
            if method == "GET":
                return self.session.get(url, params=params)
            elif method == "POST":
                return self.session.post(url, params=params)
            elif method == "PUT":
                return self.session.put(url)
            elif method == "DELETE":
                return self.session.delete(url)
            else:
                self.logger.error("unknown request type: {0}".format(method))
        except Exception as e:
            self.logger.error("problem making HTTP request: {0}".format(e))
        return None

    def request_with_retries(self, url, params=None, method="GET"):
        """Call the given request, returning the response or None if error.

        Retry the request up to NUM_RETRIES times if:

        1) execute_request() returns None, which would indicate a problem caught the request
        library. These would include network connectivity issues or request timeouts.

        OR

        2) the server returns a 50X response code. Note that 30X, and 40X responses are not errors
        that could benefit from retries, so are returned immediately.

        Args:
            url: The URL to call.
            params: The optional parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.

        Returns:
            The server response or None.
        """
        retries = 0
        delay = INITIAL_RETRY_DELAY
        while True:
            pass
            response = self.execute_request(url, params=params, method=method)

            if response:
                if response.status_code < 500:
                    return response
                else:
                    self.logger.error("from API server. Response: {0} {1}.".
                                      format(response.status_code, response.reason))

            if retries == NUM_RETRIES:
                break

            # Jitter: avoid hitting servers at fixed times or with fixed delays. Instead,
            # prevent client synchronization and server overloads by varying access times.
            jittered_delay = self.jitter(delay, JITTER_FACTOR)

            # retries + 1: Use natural numbers for readability.
            self.logger.error(
                "failed request {0} of {1} to URL '{2}'. Retrying in {3:.1f} seconds.".format(
                    retries + 1, NUM_RETRIES + 1, url, jittered_delay))

            # Exponential backoff: Double the delay between each retry, or equivilently,
            #     delay = INITIAL_RETRY_DELAY * 2 ** retries
            # The constant, 2 in this case, or doubling each delay, doesn't matter so long as the
            # delay increases significantly with each retry, allowing congestion at the server
            # to disperse.
            delay *= 2
            retries += 1
            time.sleep(jittered_delay)

        self.logger.error("maximum HTTP request attempts ({0}) exceeded to URL '{1}'.".format(
            NUM_RETRIES + 1, url))
        return None

    def make_request(self, url, params=None, method="GET", parse_json=False):
        """Create and make the given request, returning the result as JSON if requested.
        Return None on error, including HTTP errors."""
        response = self.request_with_retries(url, params=params, method=method)
        if response is None:
            return None
        elif response.status_code < 200 or response.status_code >= 300:
            self.logger.error("sent {0} to url {1} with parameters {2}. Response: {3} {4}".
                              format(method, url, params, response.status_code, response.reason))
            return None

        if not parse_json:
            return response

        try:
            return response.json()
        except:
            self.logger.error("unable to parse JSON")
        return None

    def jitter(self, interval, factor):
        """Return the interval +/- a randomized amount of the interval.

        Example:
            To jitter t by 20%: t = jitter(t, 0.20)
            Ie, if t = 10.0, the resulting t will be in {8.0, 12.0}

        Args:
            interval: a time period to be jittered.
            factor: the portion of interval to include in the randomization, expressed as a float
                    between 0.0 and 1.0.
        """
        return interval + interval * factor * (2.0 * random.random() - 1.0)
