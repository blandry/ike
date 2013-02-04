from urllib import urlencode
from urllib2 import urlopen
from utils import gpolycodec
import math
import json
import settings
from datetime import timedelta

class Directions():
    def __init__(self, steps, duration, start_location, end_location, polyline, start_address, end_address, copyrights="", warnings=[]):
        self.steps = steps
        self.duration = duration
        self.start_location = start_location
        self.end_location = end_location
        self.polyline = polyline
        self.start_address = start_address
        self.end_address = end_address
        self.copyrights = copyrights
        self.warnings = warnings
        
    @property
    def formatted_duration(self):
        td = timedelta(seconds=self.duration)
        days = td.days
        hours = td.seconds//3600 + 24*days
        minutes = (td.seconds//60)%60
        fdt = ""
        if hours > 1:
            fdt += str(hours) + " hours and "
        elif hours > 0:
            fdt += str(hours) + " hour and "
        if minutes > 1:
            fdt += str(minutes) + " minutes"
        elif minutes > 0:
            fdt += str(minutes) + " minute"
        return fdt

    def get_corridors(self, max_travel_duration, corridor_duration):
        time = 0
        corridor_starts = list()
        for step in self.steps:
            if time + step.duration >= max_travel_duration:
                for segment in step.segments:
                    if time + segment.duration >= max_travel_duration:
                        corridor_starts.append((step, segment))
                        time = segment.duration - (max_travel_duration - time)
                    else:
                        time += segment.duration
            else:
                time += step.duration
        corridors = list()
        for start_step, start_segment in corridor_starts:
            time = 0
            past_start_step = False
            past_start_segment = False
            corridor = Corridor()
            for step in self.steps:
                if step == start_step:
                    past_start_step = True
                if past_start_step:
                    for segment in step.segments:
                        if segment == start_segment:
                            past_start_segment = True
                        if past_start_segment:
                            if time + segment.duration < corridor_duration:
                                corridor.add_location(segment.end_location)
                            time += segment.duration
                        if time >= corridor_duration:
                            break
                if time >= corridor_duration:
                    corridors.append(corridor)
                    break
        return corridors

    @staticmethod
    def generate_from_google(origin, destination, sensor='false', base_url='https://maps.googleapis.com/maps/api'):
        querystring = urlencode({'origin': origin,
                                 'destination': destination,
                                 'sensor': sensor})
        url = "%s/directions/json?%s" % (base_url, querystring)
        request = urlopen(url)
        directions_json = json.load(request)
        if directions_json.get("status") != "OK":
            return None
        leg_json = directions_json.get("routes")[0].get("legs")[0]
        steps = list()
        for step_json in leg_json.get("steps"):
            start_location = Location(step_json.get("start_location").get("lat"), step_json.get("start_location").get("lng"))
            end_location = Location(step_json.get("end_location").get("lat"), step_json.get("end_location").get("lng"))
            duration = max([step_json.get("duration").get("value"), 1.0])
            speed = step_json.get("distance").get("value")/duration
            step_polyline = step_json.get("polyline").get("points")
            steps.append(Step(start_location, end_location, duration, speed, step_polyline))
        duration = leg_json.get("duration").get("value")
        start_location = Location(leg_json.get("start_location").get("lat"), leg_json.get("start_location").get("lng"))
        end_location = Location(leg_json.get("end_location").get("lat"), leg_json.get("end_location").get("lng"))
        polyline = directions_json.get("routes")[0].get("overview_polyline").get("points")
        start_address = leg_json.get("start_address")
        end_address = leg_json.get("end_address")
        copyrights = directions_json.get("routes")[0].get("copyrights")
        warnings = directions_json.get("routes")[0].get("warnings")
        return Directions(steps, duration, start_location, end_location, polyline, start_address, end_address, copyrights, warnings)

class Step():
    def __init__(self, start_location, end_location, duration, speed, polyline):
        self.start_location = start_location
        self.end_location = end_location
        self.duration = duration
        self.speed = speed
        self.polyline = polyline

    @property
    def segments(self):
        if not hasattr(self, 'generated_segments'):
            points = gpolycodec.decode(self.polyline)
            segments = list()
            for i in range(len(points)-1):
                sloc = Location(points[i][0], points[i][1])
                eloc = Location(points[i+1][0], points[i+1][1])
                seg = Segment(sloc, eloc, self.speed)
                segments.append(seg)
            self.generated_segments = segments
        return self.generated_segments

class Segment():
    def __init__(self, start_location, end_location, speed=-1):
        self.start_location = start_location
        self.end_location = end_location
        self.speed = speed

    @property
    def distance(self):
        if not hasattr(self, 'generated_distance'):
            lat1 = self.start_location.lat
            lng1 = self.start_location.lng
            lat2 = self.end_location.lat
            lng2 = self.end_location.lng
            degrees_to_radians = math.pi/180.0
            phi1 = (90.0 - lat1)*degrees_to_radians
            phi2 = (90.0 - lat2)*degrees_to_radians
            theta1 = lng1*degrees_to_radians
            theta2 = lng2*degrees_to_radians
            cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2)+math.cos(phi1)*math.cos(phi2))
            arc = math.acos(cos)
            distance = arc*settings.EARTH_RADIUS
            self.generated_distance = distance
        return self.generated_distance

    @property
    def duration(self):
        if self.speed <= 0:
            return 0.00
        return self.distance/self.speed

class Location():
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng

class Corridor():
    def __init__(self):
        self.locations = list()
        self.hotels = list()

    @property
    def polyline(self):
        return gpolycodec.encode_coords([(loc.lat, loc.lng) for loc in self.locations])

    def add_location(self, location):
        self.locations.append(location)

    def get_hotels(self, hotel_model, max_hotel_price, early_weight, detour_weight):
        hotels_in_corridor_range = list()
        hotels_heuristics = list()
        i = 0
        for loc in self.locations:
            i += 1
            if i % 5 == 0:
                hotels_in_point_range = hotel_model.query.filter(hotel_model.price<=max_hotel_price).filter(hotel_model.lat_min<=loc.lat).filter(hotel_model.lat_max>=loc.lat)
                hotels_in_point_range = hotels_in_point_range.filter(hotel_model.lng_min<=loc.lng).filter(hotel_model.lng_max>=loc.lng).all()
                for hotel in hotels_in_point_range:
                    if hotel not in hotels_in_corridor_range:
                        hotels_in_corridor_range.append(hotel)
                        heuristic = early_weight*i+detour_weight*(abs(hotel.lat-loc.lat)+abs(hotel.lng-loc.lng))
                        hotels_heuristics.append(heuristic)
        candidates = zip(hotels_in_corridor_range, hotels_heuristics)
        candidates = sorted(candidates, key=lambda candidate: candidate[1])
        results = [c[0] for c in candidates]
        return results

    def generate_hotels(self, hotel_model, max_hotel_price, early_weight, detour_weight):
        self.hotels = self.get_hotels(hotel_model, max_hotel_price, early_weight, detour_weight)

    @property
    def has_hotels(self):
        return len(self.hotels)>0
