# eo-python

Electric Objects python library

##Warning: This currently doesn't work ;)


##Example


```python

if __name__ == "__main__":
    #How to use this dude:
    #instantiate it. yay!
    username = '' #Email
    password = '' #Hope your password is strong and unique!
    eo = electric_object(username=username, password=password)
    favs = eo.display_random_favorite()

    #Let's favorite and unfavorite medias:
    #now favorite
    #print eo.favorite("5626")
    #now unfavorite
    #print eo.unfavorite("5626")

    #Displaying in
    #Display a URL
    #art = ['5568','1136']
    #print eo.display("1136")

    #Let's set a url
    #print eo.set_url("http://www.harperreed.com/")
    
```