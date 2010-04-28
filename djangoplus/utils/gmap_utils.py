import urllib

from django.conf import settings
from django.db import models

class AbstractGMapLocalized(models.Model):
    map_latitude = models.FloatField(null=True, blank=True)
    map_longitude = models.FloatField(null=True, blank=True)
    map_manual_localized = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_google_maps_url(self):
        return "http://local.google.com/maps?f=q&hl=pt-BR&ll=%s,%s" %(self.map_latitude, self.map_longitude)

    def get_latitude(self):
        return self.map_latitude and "%.6f" % float(self.map_latitude) or None

    def get_longitude(self):
        return self.map_longitude and "%.6f" % float(self.map_longitude) or None

    def localization_default(self):
        """Retorns true if this is in default locazation"""
        return (not self.map_latitude and not self.map_longitude) or \
                (float(self.map_latitude) == settings.GOOGLE_MAPS_LATITUDE_DEFAULT and \
                 float(self.map_longitude) == settings.GOOGLE_MAPS_LONGITUDE_DEFAULT)

    def get_full_address(self):
        return ''

def get_geocode(address):
    """http://www.djangosnippets.org/snippets/293/"""
    try:
        import urllib

        key = settings.GOOGLE_MAPS_API_KEY
        output = "csv"
        location = urllib.quote_plus(address.encode('utf-8'))
        url = "http://maps.google.com/maps/geo?q=%s&output=%s&key=%s" % (location, output, key)
        data = urllib.urlopen(url).read()
        dlist = data.split(',')

        if dlist[0] == '200':
            return dlist[2], dlist[3]
        else:
            return None, None
    except Exception, e:
        return None, None

