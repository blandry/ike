from application import *
import settings
import csv
import sys

def load_hotels():

    hotel_type_names = ['Hotel', 'Motel', 'Inn', 'Bed & Breakfast', 'Vacation Rental', 'Hostel', 'Retreat', 'Resort', 'Other', 'Apartment']
    types = list()
    for name in hotel_type_names:
        type = HotelType(name)
        db.session.add(type)
        types.append(type)
    print("Hotel types loaded...")

    reader = csv.reader(open("data/facilitieskey.csv"))
    facilities = dict()
    for id, name in reader:
        if name != '':
            facility = HotelFacility(name, int(id))
            db.session.add(facility)
            facilities[int(id)] = facility
    print("Hotel facilities loaded...")

    i = 0
    sys.stdout.write("Entries loaded: [%s]" % i)
    sys.stdout.flush()
    reader = csv.reader(open("data/hotelsbase.csv"), delimiter="~")
    keys = ['hotelsbase_id', 'name', 'stars', 'price', 'city', 'state', 'country_code', 'country', 'address', 'location', 'url', 
            'tripadvisor_url', 'lat', 'lng', 'latlng', 'hotel_type', 'chain_id', 'rooms', 'hotel_facilities', 'check_in', 
            'check_out', 'rating']
    reader.next() # skips the header
    for entry in reader:
        values = dict()
        for key, value in zip(keys, entry):
            if value != '':
                if key in ['hotelsbase_id', 'price', 'latlng', 'chain_id', 'rooms']:
                    try:
                        value = int(value)
                    except:
                        value = None
                elif key in ['stars', 'lat', 'lng', 'rating']:
                    try:
                        value = float(value)
                    except:
                        value = None
                elif key == 'hotel_type':
                    try:
                        value = types[int(value)]
                    except:
                        value = None
                elif key == 'hotel_facilities':
                    fkeys = list()
                    for fkey in value.split("|"):
                        try:
                            fkeys.append(int(fkey))
                        except:
                            pass
                    value = [facilities.get(k) for k in fkeys if k in facilities.keys()] 
                else:
                    try:
                        value = unicode(value)
                    except:
                        value = None
                if value:
                    values[key] = value
        if values.get("country_code", "") in settings.COUNTRIES_TO_LOAD:
            hotel = Hotel(values)
            db.session.add(hotel)
            i += 1
        if i % 1000 == 0:
            db.session.flush()
            sys.stdout.write("\rEntries loaded: [%s]" % i)
            sys.stdout.flush()
    db.session.flush()
    sys.stdout.write("\rEntries loaded: [%s]" % i)
    sys.stdout.flush()

    db.session.commit()
    print(" ...Success!")

if __name__=="__main__":
    load_hotels()
