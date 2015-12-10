"""
    Here is a wrapper for the *unreleased* electric objects API.
    Built by
    - Harper Reed (harper@nata2.org) - @harper
    - Gary Boone (gary.boone@gmail.com) - github.com/GaryBoone

    The Electric Objects API is not yet supported by Electric Objects. It may change or
    stop working at any time.

    See the __main__ below for example API calls.

    As configured, this module will display a random image from the favorites you marked on
    electricobjects.com.

    To use as is, you need to set your electricobjects.com login credentials. See the
    get_credentials() function for how to do so.

    Note, due a limitation of the API, or our understanding of it, only the first 20 favorites
    are returned by the API. So the randomized image is picked among only the first
    20 images shown on your favorites page on electricobjects.com.

    Usage: $ python eo.py

    Written for Python 2.7.x.
"""

from lxml import html
import os
import random
import requests

CREDENTIALS_FILE = '.credentials'
USER_ENV_VAR = 'EO_USER'
PASSWORD_ENV_VAR = 'EO_PASS'


class ElectricObject:
    """The ElectricObject provides the functions for the electric objects API calls.

    It maintains the state of credentials and the currently signed-in session.
    Usage: instantiate the object with credentials, then make one or more API calls
    with the object.
    """
    base_url = 'https://www.electricobjects.com/'

    def __init__(self, username, password):
        """Upon initialization, set the credentials. But don't attempt to sign-in until
        an API call is made.
        """
        self.username = username
        self.password = password
        self.signed_in_session = None

    def signin(self):
        """ Sign in. If successful, set self.signed_in_session to the session for reuse in
        subsequent requests. If not, set self.signed_in_session to None.

        Note that while the session in self.signed_in_session can be reused for subsequent
        requests, the sign-in may expire after some time. So requests that fail should
        try signing in again.
        """
        self.signed_in_session = None
        try:
            session = requests.Session()
            signin_response = session.get('https://www.electricobjects.com/sign_in')
            if signin_response.status_code != requests.codes.ok:
                print 'Error: unable to sign in. Status: ', signin_response.status_code, ", response: ", signin_response.text
                return
            tree = html.fromstring(signin_response.content)
            authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
            if authenticity_token == "":
                return
            payload = {
                "user[email]": self.username,
                "user[password]": self.password,
                "authenticity_token": authenticity_token
            }
            p = session.post('https://www.electricobjects.com/sign_in', data=payload)
            if p.status_code != requests.codes.ok:
                print 'Error: unable to sign in. Status: ', p.status_code, ", response: ", requests.text
                return
            self.signed_in_session = session
        except Exception as e:
            print e

    def signed_in(self):
        """ Return true if we have a valid signed-in session. """
        return self.signed_in_session is not None

    def make_request(self, path, params=None, method='GET'):
        """Create a request of the given type and make the request to the Electric Objects API.

        Args:
            path: The request target path for the URL.
            params: The URL parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.

        Returns:
            The request result or None.
        """
        if not self.signed_in():
            self.signin()
            if not self.signed_in():
                return None

        url = self.base_url + path
        # TODO(gary): These requests should retry in case the sign-in has expired.
        if method == "GET":
            return self.signed_in_session.get(url, params=params)
        elif method == "POST":
            return self.signed_in_session.post(url, params=params)
        elif method == "PUT":
            return self.signed_in_session.put(url)
        elif method == "DELETE":
            return self.signed_in_session.delete(url)

        print 'Error: Unknown request type in make_request'
        return None

    def user(self):
        """Obtain the user information."""
        path = "/api/beta/user/"
        return self.make_request(path, method='GET')

    def favorite(self, media_id):
        """Set a media as a favorite by id."""
        path = "/api/beta/user/artworks/favorited/" + media_id
        return self.make_request(path, method='PUT')

    def unfavorite(self, media_id):
        """Remove a media as a favorite by id."""
        path = "/api/beta/user/artworks/favorited/" + media_id
        return self.make_request(path, method='DELETE')

    def display(self, media_id):
        """Display media by id."""
        path = "/api/beta/user/artworks/displayed/" + media_id
        return self.make_request(path, method='PUT')

    def favorites(self):
        """Return the user's list of favorites in JSON else [].

        Note: At present, the API only returns the first 20 favorites.

        Returns:
            The array of favorites in JSON format or else an empty list.
        """
        path = "/api/beta/user/artworks/favorited"
        response = self.make_request(path, method='GET')
        if response is None:
            return []
        elif response.status_code != requests.codes.ok:
            print "Error in favorites(): HTML response", response.status_code, response.reason
            return []
        try:
            return response.json()
        except:
            print "Error in favorites(): unable to parse JSON"
        return []

    def display_random_favorite(self):
        """Retrieve the user's favorites and display one of them randomly.

            Note that at present, only the first 20 favorites are returned by the API.

            TODO(gary): It's possible to return the same favorite that is already displayed.
            Better: get the id of the currently displayed image and ensure the new one is
            different.

            Returns:
                The id of the displayed favorite, else 0.
        """
        favs = self.favorites()
        if favs == []:
            return 0
        fav = random.choice(favs)
        media_id = str(fav['artwork']['id'])
        print media_id
        return self.display(media_id)

    def set_url(self, url):
        """Set a URL to be on the display.
        Note: IN PROGRESS. This function does not successfully display a URL on the EO1 currently.
        """
        url = "set_url"
        with requests.Session() as s:
            eo_sign = s.get('https://www.electricobjects.com/sign_in')
            authenticity_token = eo_sign.text.encode('utf-8').strip().split("name=\"authenticity_token\" type=\"hidden\" value=\"")[1].split("\" /></div>")[0]
            payload = {
                "user[email]": self.username,
                "user[password]": self.password
            }
            payload['authenticity_token'] = authenticity_token
            p = s.post('https://www.electricobjects.com/sign_in', data=payload)
            if p.status_code == 200:
                eo_sign = s.get('https://www.electricobjects.com/set_url')
                authenticity_token = eo_sign.text.encode('utf-8').strip().split("name=\"authenticity_token\" type=\"hidden\" value=\"")[1].split("\" /></div>")[0]
                print authenticity_token
                params = {
                  "custom_url": url,
                  "authenticity_token": authenticity_token
                }
                r = s.post(self.base_url + url, params=params)
                if r.status_code == 200:
                    return True
                else:
                    return False


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
    username = ''  # You can set them here if you don't plan on uploading this code to GitHub.
    password = ''

    username = os.environ[USER_ENV_VAR] if USER_ENV_VAR in os.environ else username
    password = os.environ[PASSWORD_ENV_VAR] if PASSWORD_ENV_VAR in os.environ else password

    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            username = next(f).strip()
            password = next(f).strip()
    except:
        pass  # Fail silently if no file, missing lines, or other problem.

    return {"username": username, "password": password}


def main():
    """An example main that displays a random favorite."""

    # Display a random favorite.
    credentials = get_credentials()
    eo = ElectricObject(username=credentials["username"], password=credentials["password"])
    eo.display_random_favorite()

    # Mark a media item as a favorite.
    # print eo.favorite("5626")
    # Now unfavorite it.
    # print eo.unfavorite("5626")

    # Display a media item by id.
    # print eo.display("1136")

    # Let's set a URL.
    # print eo.set_url("http://www.harperreed.com/")


if __name__ == "__main__":
    main()
