# eo-python

Unofficial Electric Objects Python Library

## Overview

The eo-python demonstrates how to control the Electric Objects EO1 using their *unsupported* beta API and Python. 

In addition to demonstrating several kinds of API calls, eo-python out-of-the-box will randomly display one of your favorites. 

This code was written by [Harper Reed](https://github.com/harperreed) and [Gary Boone](https://github.com/garyboone).


## Implementation

This code demonstrates how to call Electric Objects' API. That is, the code makes calls to Electric Objects' servers, which then communicate with your EO1 device. It does not directly communicate with your EO1 device.

To use it, set your electricobjects.com login credentials. You can do that by inserting them into the code, using environment variables, or creating a .credentials file in the same directory as the code. See the *get_credentials()* function in eo.py for details.

As configured, this module will display a random image from the favorites you marked on electricobjects.com each time it is run. It can be used to implement a long-requested feature of the EO1: automatic rotation among favorites. To do so, set up your operating system to run this code periodically, say every few hours. For more on this topic, see Automation below.


## Limitations

* Electric Objects' API is unsupported and my disappear at any time.
* Due a limitation of the API, or our understanding of it, only the first 20 items are returned by API calls that return lists, such as favorites and devices. So the randomized image is picked among only the first 20 images shown on your favorites page on electricobjects.com.
* The *set_url()* function does not currently work correctly.
* The code does not demonstrate all of the API calls and usage, but only ones we found by experimentation.


## Code Notes

* Written for Python 2.7.x. 
* Tested on OSX El Capitan.
* Usage: $ python eo.py


## Coding Example


```python

    credentials = get_credentials()
    eo = ElectricObject(username=credentials["username"],
                        password=credentials["password"])

    # Display a random favorite.
    eo.display_random_favorite()

    # Mark a media item as a favorite.
    print eo.favorite("5626")
    # Now unfavorite it.
    print eo.unfavorite("5626")

    # Display a media item by id.
    print eo.display("1136")

    # List user's devices
    print eo.devices()
        
```

## Automation

The script is designed to display a new favorite on the EO1 each time it is run. To automatically update your EO1 artwork periodically, use your operating system's standard method for periodically running scripts. On Linux, it's cron. On Macs, it's launchd.


#### [Mac OSX only]
The script eo.py can be configured to run under OSX's launchd facility. Help for launchd can be found on the web. For example, see [launchd.info](http://launchd.info/), which includes examples for the easy-to-use [LaunchControl](http://www.soma-zone.com/LaunchControl/) application.


## License ##
The code is available at GitHub [HarperReed/eo-python](https://github.com/harperreed/eo-python) under the [MIT license](http://opensource.org/licenses/mit-license.php).