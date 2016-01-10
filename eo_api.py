import eo_net
import logging
import requests
import time


# How often should we sign-in?
SIGNIN_INTERVAL_IN_HOURS = 4  # hours

USER_AGENT = "eo-python-client"


class EO_API(object):
    """The API class provides functions for the Electric Objects API calls.

    It maintains the state of credentials and the currently signed-in session.
    Usage: instantiate the object with credentials, then make one or more API calls
    with the object.

    Upon initialization, set the credentials. But don't attempt to sign-in until
    an API call is made.
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
        self.logger = logging.getLogger(".".join(["eo", self.__class__.__name__]))
        signin_url = self.base_url + "sign_in"
        self.username = username
        self.password = password
        self.signin_url = signin_url
        self.last_signin_time = 0

        self.net = eo_net.EO_Net()

    def signin(self):
        """Sign in. If successful, set self.session to the session for reuse in
        subsequent requests. If not, set self.session to None.

        Note that while the session in self.session can be reused for subsequent
        requests, the sign-in may expire after some time. So requests that fail should
        try signing in again.
        """
        new_session = requests.Session()
        new_session.headers["User-Agent"] = USER_AGENT
        self.net.set_session(new_session)
        payload = {
            "user[email]": self.username,
            "user[password]": self.password
        }
        success = self.net.post_with_authenticity(self.signin_url, payload)
        if not success:
            self.net.set_session(None)
            return
        self.last_signin_time = time.clock()

    def signed_in(self):
        """Return true if we have a valid signed-in session. """
        return self.net.get_session() is not None

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

    def make_request(self, endpoint, params=None, method="GET", path_append=None, parse_json=False):
        """Create a request of the given type and make the request to the Electric Objects API.

        Args:
            endpoint: The id of the request target API path in self.endpoints.
            params: The URL parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.
            path_append: An additional string to add to the URL, such as an ID.
            parse_json: attempt to parse the result as JSON if True.

        Returns:
            The servers response, as JSON if requested, or None.
        """
        # Check sign-in
        signin_ok = self.check_signin_status()
        if not signin_ok:
            return None

        if endpoint not in self.endpoints.keys():
            self.logger.error("unknown endpoint requested: " + endpoint)
            return None

        url = self.base_url + self.api_version_path + self.endpoints[endpoint]
        if path_append:
            url += path_append

        return self.net.make_request(url, params=params, method=method, parse_json=parse_json)
