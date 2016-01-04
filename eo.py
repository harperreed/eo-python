# -*- coding: utf-8 -*-
"""
    Here is a wrapper for the *unreleased* electric objects API.
    Built by
    • Harper Reed (harper@nata2.org) - @harper
    • Gary Boone (gary.boone@gmail.com) - github.com/GaryBoone

    The Electric Objects API is not yet supported by Electric Objects. It may change or
    stop working at any time.

    See the __main__ below for example API calls.

    As configured, this module will display a random image from the favorites you marked on
    electricobjects.com.

    To use as is, you need to set your electricobjects.com login credentials. See the
    get_credentials() function for how to do so.

    Randomized images are picked among the first 200 images shown on your favorites page on
    electricobjects.com. Change MAX_FAVORITES_FOR_DISPLAY below to adjust this limit.

    Usage: $ python eo.py

    Written for Python 2.7.x.
"""

import datetime
from lxml import html
import os
import random
import requests
import time

CREDENTIALS_FILE = ".credentials"
USER_ENV_VAR = "EO_USER"
PASSWORD_ENV_VAR = "EO_PASS"
USER_AGENT = "eo-python-client"

# The maximum number of favorites to consider for randomly displaying one.
MAX_FAVORITES_FOR_DISPLAY = 200

# The number of favorites to pull per request.
NUM_FAVORITES_PER_REQUEST = 30

# BEST PRACTICE: don't hit server at maximum rate.
# Minimum time between requests.
MIN_REQUEST_INTERVAL = 0.75  # seconds, float

# How often should we sign-in?
SIGNIN_INTERVAL_IN_HOURS = 4  # hours

# BEST PRACTICE: If you do retries, back them off exponentially. If the server is down
# or struggling to come back up, you'll avoid creating a stampede of clients retrying
# their requests.
# What's the first retry delay? If more retries are needed, double each delay.
INITIAL_RETRY_DELAY = 4.0  # seconds, float

# In this code, if there's a missed update, we can just wait until the next scheduled update
# to try again. So we don't need to retry many times.
# The number of retry attempts.
NUM_RETRIES = 4


def log(msg):
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H:%M:%S")
    print "{0}: {1}".format(timestamp, msg)


class ElectricObject:
    """The ElectricObject class provides the functions for the Electric Objects API calls.

    It maintains the state of credentials and the currently signed-in session.
    Usage: instantiate the object with credentials, then make one or more API calls
    with the object.
    """

    # Class variables
    base_url = "https://www.electricobjects.com/"
    api_version_path = "api/v2/"
    endpoints = {
        "user": "user/",
        "devices": "user/devices/",
        "displayed": "user/artworks/displayed/",
        "favorited": "user/artworks/favorited/"
        }

    def __init__(self, username, password):
        """Upon initialization, set the credentials. But don't attempt to sign-in until
        an API call is made.
        """
        self.username = username
        self.password = password
        self.signed_in_session = None
        self.last_request_time = 0
        self.last_signin_time = 0

    def request_authenticity_token(self, path):
        """Request, parse, and return the authenticity token needed to post to the given path."""
        authenticity_token = ""

        # Request the page with the token.
        self.check_request_rate()
        url = self.base_url + path
        response = self.request_with_retries(url)
        if not response:
            log("Error: unable to read {0}.".format(url))
            return ""
        elif response.status_code != requests.codes.ok:
            log("Error: unable to read: {0}. Status: {1}, response: {2}".
                format(url, response.status_code, response.text))
            return ""

        # Parse out the token.
        try:
            tree = html.fromstring(response.content)
            authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
        except Exception as e:
            log("Error: problem parsing authenticity token: " + str(e))
        return authenticity_token

    def post_payload(self, path, payload, authenticity_token):
        """Post the given payload to the endpoint given by path.

        Args:
            path: the path from the base_url.
            payload: the key/values to post.
            authenticity_token: the required auth token.

        Returns:
            The response, else None.
        """
        if not authenticity_token:
            return None

        url = self.base_url + path
        self.check_request_rate()
        response = self.request_with_retries(url, method="POST", params=payload)
        if response and response.status_code == requests.codes.ok:
            return response

        if not response:
            log("Error: unable to post to {0}.".format(url))
        else:
            log("Error: unable to post to {0}. Status: {1}, response: {2}".
                format(url, response.status_code, response.text))
        return None

    def signin(self):
        """Sign in. If successful, set self.signed_in_session to the session for reuse in
        subsequent requests. If not, set self.signed_in_session to None.

        Note that while the session in self.signed_in_session can be reused for subsequent
        requests, the sign-in may expire after some time. So requests that fail should
        try signing in again.
        """
        self.signed_in_session = requests.Session()
        self.signed_in_session.headers["User-Agent"] = USER_AGENT
        authenticity_token = self.request_authenticity_token("sign_in")
        payload = {
            "user[email]": self.username,
            "user[password]": self.password,
            "authenticity_token": authenticity_token
        }
        success = self.post_payload("sign_in", payload, authenticity_token)
        if not success:
            self.signed_in_session = None
            return
        self.last_signin_time = time.clock()

    def signed_in(self):
        """Return true if we have a valid signed-in session. """
        return self.signed_in_session is not None

    def check_signin_status(self):
        """Check if think we're signed in or whether enough time has passed that we
        should sign in again.
        """
        time_since_signin = time.clock() - self.last_signin_time
        if not self.signed_in() or time_since_signin > SIGNIN_INTERVAL_IN_HOURS * 3600.0:
            self.signin()
            if not self.signed_in():
                return False
        return True

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
                return self.signed_in_session.get(url, params=params)
            elif method == "POST":
                return self.signed_in_session.post(url, params=params)
            elif method == "PUT":
                return self.signed_in_session.put(url)
            elif method == "DELETE":
                return self.signed_in_session.delete(url)
            else:
                log("Unknown request type: {0}".format(method))
        except Exception as e:
            log("Error in making HTTP request: {0}".format(e))
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
                    log("Error from API server. Response: {0} {1}.".
                        format(response.status_code, response.reason))

            if retries == NUM_RETRIES:
                break

            # retries + 1: Use natural numbers for readability.
            jittered_delay = jitter(delay, 0.20)
            log("Error: Failed request {0} of {1}. Retrying in {2} seconds.".
                format(retries + 1, NUM_RETRIES + 1, jittered_delay))

            # Exponential backoff: Double the delay between each retry, or equivilently,
            #     delay = INITIAL_RETRY_DELAY * 2 ** retries
            # The constant, 2 in this case, or doubling each delay, doesn't matter so long as the
            # delay increases significantly with each retry, allowing congestion at the server
            # to disperse.
            delay *= 2
            retries += 1
            time.sleep(jittered_delay)

        log("Error: Maximum HTTP request attempts ({0}) exceeded.".format(NUM_RETRIES + 1))
        return None

    def make_request(self, endpoint, params=None, method="GET", path_append=None):
        """Create a request of the given type and make the request to the Electric Objects API.

        Args:
            endpoint: The id of the request target API path in self.endpoints.
            params: The URL parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.
            path_append: An additional string to add to the URL, such as an ID.

        Returns:
            The request result or None.
        """
        # Check sign-in
        signin_ok = self.check_signin_status()
        if not signin_ok:
            return None

        # Build URL.
        url = self.base_url + self.api_version_path + self.endpoints[endpoint]
        if path_append:
            url += path_append

        # Call API with retries and exponential backoff.
        return self.request_with_retries(url, method=method, params=params)

    def make_JSON_request(self, endpoint, params=None, method="GET", path_append=None):
        """Create and make the given request, returning the result as JSON, else []."""
        response = self.make_request(endpoint, params=params, method=method, path_append=path_append)
        if response is None:
            return []
        elif response.status_code != requests.codes.ok:
            log("Error in make_JSON_request(). Response: {0} {1}".
                format(response.status_code, response.reason))
            return []
        try:
            return response.json()
        except:
            log("Error in make_JSON_request(): unable to parse JSON")
        return []

    def user(self):
        """Obtain the user information."""
        return self.make_request("user", method="GET")

    def favorite(self, media_id):
        """Set a media as a favorite by id."""
        return self.make_request("favorited", method="PUT", path_append=media_id)

    def unfavorite(self, media_id):
        """Remove a media as a favorite by id."""
        return self.make_request("favorited", method="DELETE", path_append=media_id)

    def display(self, media_id):
        """Display media by id."""
        return self.make_request("displayed", method="PUT", path_append=media_id)

    def favorites(self):
        """Return the user's list of favorites in JSON else [].

        Returns:
            An array of up to NUM_FAVORITES_PER_REQUEST favorites in JSON format
            or else an empty list.
        """
        offset = 0
        favorites = []
        while True:
            params = {
              "limit": NUM_FAVORITES_PER_REQUEST,
              "offset": offset
            }
            result_JSON = self.make_JSON_request("favorited", method="GET", params=params)
            if not result_JSON:
                break
            favorites.extend(result_JSON)
            if len(result_JSON) < NUM_FAVORITES_PER_REQUEST:  # last page
                break
            if len(favorites) > MAX_FAVORITES_FOR_DISPLAY:  # too many
                favorites = favorites[:MAX_FAVORITES_FOR_DISPLAY]
                break
            offset += NUM_FAVORITES_PER_REQUEST
        return favorites

    def devices(self):
        """Return a list of devices in JSON format, else []."""
        return self.make_JSON_request("devices", method="GET")

    def choose_random_item(self, items, excluded_id=None):
        """Return a random item, avoiding the one with the excluded_id, if given.
        Args:
            items: a list of Electric Objects artwork objects.

        Returns:
            An artwork item, which could have the excluded_id if there's only one choice,
            or [] if the list is empty.
        """
        if not items:
            return []
        if len(items) == 1:
            return items[0]
        if excluded_id:
            items = [item for item in items if item["artwork"]["id"] != excluded_id]
        return random.choice(items)

    def current_artwork_id(self, device_json):
        """Return the id of the artwork currently displayed on the given device.

        Args:
            device_json: The JSON describing the state of a device.

        Returns:
            An artwork id or 0 if the id isn't present in the device_json.
        """
        if not device_json:
            return 0
        id = 0
        try:
            id = device_json["reproduction"]["artwork"]["id"]
        except KeyError as e:
            log("Error parsing device JSON. Missing key: {0}".format(e))
        return id

    def display_random_favorite(self):
        """Retrieve the user's favorites and display one of them randomly on the first device
        associated with the signed-in user.

        Note that at present, only the first 20 favorites are returned by the API.

        A truely random choice could be the one already displayed. To avoid that, first
        request the displayed image and remove it from the favorites list, if present.

        Note:
            This function works on the first device if there are multiple devices associated
            with the given user.

        Returns:
            The id of the displayed favorite, else 0.
        """
        devs = self.devices()
        if not devs:
            log("Error in display_random_favorite: no devices returned.")
            return 0
        device_index = 0  # First device of user.
        current_image_id = self.current_artwork_id(devs[device_index])

        favs = self.favorites()
        if favs == []:
            return 0
        fav_item = self.choose_random_item(favs, current_image_id)
        if not fav_item:
            return 0
        fav_id = fav_item["artwork"]["id"]
        self.display(str(fav_id))
        return fav_id

    def set_url(self, url):
        """Display the given URL on the first device associated with the signed-in user.
        Return True on success.
        """
        devs = self.devices()
        if not devs:
            log("Error in set_url: no devices returned.")
            return 0
        device_index = 0  # First device of user.
        device_id = devs[device_index]["id"]

        authenticity_token = self.request_authenticity_token("set_url")
        params = {
          "device_id": device_id,
          "custom_url": url,
          "authenticity_token": authenticity_token
        }
        r = self.post_payload("set_url", params, authenticity_token)
        return r.status_code == requests.codes.ok


def jitter(interval, factor):
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


def get_credentials():
    """Obtains the electricobjects.com username and password. They can be set here in the code,
    in environment variables, or in a file named by CREDENTIALS_FILE.

    A simple way to set them in the environment variables is prefix your command with them.
    For example:
        $ EO_USER=you@example.com EO_PASS=pword python eo.py

    Don't forget to clear your command history if you don't want the credentials stored.

    This function allows us to avoid uploading credentials to GitHub. In addition to not
    writing them here, the credentials filename is included in the .gitignore file.

    The sources are read in the order of: default, then environment variables, then file.
    Each source overwrites the username and password separately, if set in that source.

    Returns:
        A dictionary with key/values for the username and password.
    """
    username = ""  # You can set them here if you don"t plan on uploading this code to GitHub.
    password = ""

    username = os.environ[USER_ENV_VAR] if USER_ENV_VAR in os.environ else username
    password = os.environ[PASSWORD_ENV_VAR] if PASSWORD_ENV_VAR in os.environ else password

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            username = next(f).strip()
            password = next(f).strip()
    except:
        pass  # Fail silently if no file, missing lines, or other problem.

    return {"username": username, "password": password}


def main():
    """An example main that displays a random favorite."""

    credentials = get_credentials()
    eo = ElectricObject(username=credentials["username"], password=credentials["password"])
    displayed = eo.display_random_favorite()
    if displayed:
        log("Displayed artwork id " + str(displayed))

    time.sleep(10)

    # Let's set a URL.
    # Hmmm. This one didn't work: http://www.ustream.tv/channel/live-iss-stream/pop-out
    # The EO1 display reads: 'Missing Flash plugin'
    #
    # This one works, creating an autoplaying slideshow:
    # url = "http://theslideshow.net/#advanced/search-advanced-query=architectural+study" + \
    #       "&imageSize=Extra_Large"
    #
    # A single image, 1080x1920:
    # url = "http://hd.highresolution-wallpapers.net/wallpapers/" + \
    #       "board_circuit_silicon_chip_technology_high_resolution_wallpapers-1080x1920.jpg"
    # displayed = eo.set_url(url)
    # if displayed:
    #     log("Displayed URL " + url)

    # Mark a media item as a favorite.
    # print eo.favorite("5626")
    # Now unfavorite it.
    # print eo.unfavorite("5626")

    # Display a media item by id.
    # print eo.display("1136")

if __name__ == "__main__":
    main()
