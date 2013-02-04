from urllib import urlencode
from urllib2 import urlopen
import json
import settings

def get_restaurants_from_google(restaurant_model, lat, lng, sensor='false', apikey=settings.GOOGLE_API_KEY, baseurl='https://maps.googleapis.com/maps/api/place'):
    querystring = urlencode({'key': apikey,
                             'location': '%s,%s' % (lat, lng),
                             'rankby': 'distance',
                             'types': 'restaurant',
                             'sensor': sensor})
    url = "%s/nearbysearch/json?%s" % (baseurl, querystring)
    request = urlopen(url)
    response = json.load(request)
    if response.get("status") != "OK":
        return None
    results = list()
    for restaurant_json in response.get("results"):
        google_id = restaurant_json.get("id")
        lat = restaurant_json.get("geometry").get("location").get("lat")
        lng = restaurant_json.get("geometry").get("location").get("lng")
        name = restaurant_json.get("name")
        rating = restaurant_json.get("rating", 0.00)
        address = restaurant_json.get("vicinity")
        if name and address:
            results.append(restaurant_model(google_id, lat, lng, name, rating, address))
    return results                     
