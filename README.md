# eo-python

Unofficial Electric Objects Python Library

## Overview

The eo-python demonstrates how to control the Electric Objects EO1 using their *unsupported* API and Python. 

In addition to demonstrating several kinds of API calls, eo-python out-of-the-box will randomly display one of your favorites. 

The code also demonstrates several features of highly-reliable client software, including rate limiting and retries with limits, exponential backoff, and jitter. See below for an explanation of these best practices.

This code was written by [Harper Reed](https://github.com/harperreed) and [Gary Boone](https://github.com/garyboone).

## Installation

eo-python depends on:

* [requests](http://docs.python-requests.org/en/latest/)
* [lxml](http://lxml.de/)

These can be installed with

     $ sudo easy_install pip
     $ sudo pip install requests
     $ sudo pip install lxml

#### [Mac OSX only]
Note: if the *lxml* installation fails on OSX El Capitan with an error like "command 'cc' failed with exit status 1", then try

    $ xcode-select --install

This command does not require XCode to be installed.

#### Running

    $ python eo.py


## Design Notes

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

## Reliability Best Practices

Naively written client code can pose a threat to servers. By failing to consider scaling issues, clients can create overload conditions for servers that lead to request failures, server failures, or even complete service outages. The primary threat arises from large numbers of clients becoming synchronized, making large numbers of server requests simultaneously by chance, or by hammering overloaded servers with retry requests compounding the overload problem. Even a small number of clients can create abusive loads if they all hit servers at the same time. 

As the Electric Objects' API is not officially supported, it may not be provisioned for the kinds of loads unknown Internet clients could create. So it is imperative that clients are well-behaved. This code demonstrates several of the best practices for creating reliable clients that avoid risks of server abuse.

Independent of the Electric Objects API, this code may be useful to coders who want to understand client/server scalability issues including rate limiting, limited retries, exponential backoff, and jitter.

The key issue is that servers can be overloaded by too many simultaneous requests. Correctly written clients avoid overloading the servers by carefully avoiding synchronization and avoiding naive retries on errors. The following techniques are used. Below, we'll talk about a single server, but the principle applies to pools of servers and whole distributed systems, differing only by scale.

#### Asynchrony

Clients often operate on fixed schedules, updating their state periodically such as on the hour. Sensible enough, unless you're the server which now endures a synchronized onslaught of load every hour on the hour. Such a load is easily avoided: client programmers should choose randomized times for updates. At the very least, avoid on-the-hour or on-the-half-hour updates. Avoid wall-clock update times. Prefer every-k hours instead because every-k hours after startup will vary naturally with the client startup time. See also Jitter below.

#### Rate Limiting

The simplest best practice is to avoid making sequences of requests to servers as quickly as possible. Instead, ensure that there is some delay between subsequent requests. As most of the delay is in the network or server response time, it does little good to hit a server as quickly as possible. But spacing out server requests can make a large difference in reliability, allowing the servers to complete more requests without overloading. Just as traffic lights increase car throughout through intersections, rate limited clients increase the chance that their series of requests succeed by reducing the likelihood that the servers drop some requests as they become overloaded.

#### Limited Retries

Because we consider the network to provide unreliable connections, it makes sense to retry a request to a server if it fails. But doing so naively can decrease reliability. As a server becomes overloaded and starts to fail requests, clients retrying their requests will escalate the problem, added more and more requests. Instead, clients should retry only a limited number of times. For many applications, that's fine. In this code, if the client fails to update the artwork, it can just try again later.

#### Exponential Backoff

If a client does retry failed requests, it should not retry immediately. Instead, it should wait an exponentially increasing amount of time between retries. For example, this code waits 4, 8, 16, and 32 seconds, then gives up. That backoff time allows the load on a server to dissipate. As all of the clients notice the problem, they avoid piling onto the failing server. Such a pile-on increases the likelihood of the server failing and worse, spreading its increasing load to the other servers in its pool which having lost one of its servers then has reduced capacity, creating a cascading failure. The solution is for clients to backoff their retries. It has to be exponential because the onset of load will be exponential as more clients add more retries.

#### Jitter

Even exponential backoff isn't quite enough to save our failing server. If all of the clients backoff at the exact same schedule and remain synchronized as they do it, the server will continue to be slammed with a debilitating amount of simultaneous traffic. What could cause such a synchronization? The server failure itself! The solution is again to add variation. If a client has to retry, it should add jitter to the retry schedule. So instead of waiting 4 seconds, it should wait 4 +/- 0.8 seconds, for example. A 20% randomization maintains the exponential backoff schedule while spreading out the requests of the collection of clients that start at the same time.


## License
The code is available at GitHub [HarperReed/eo-python](https://github.com/harperreed/eo-python) under the [MIT license](http://opensource.org/licenses/mit-license.php).