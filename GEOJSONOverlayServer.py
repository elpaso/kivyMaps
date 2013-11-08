#!/usr/bin/python
# -*- coding: utf-8 -*-
from projections import *
from urllib2 import urlopen
from threading import Thread
from kivy.logger import Logger
from kivy.loader import Loader
from os.path import join, dirname
from TileServer import TileServer
import re
import time
import os
import hashlib
import json


class GEOJSONOverlayServer(object):

    cache = {}
    type = 'geojson'  # TODO: replace handling in mapviewer with action handlers in the overlay class

    def __init__(self, provider_host=None, progress_callback=None):
        self.provider_host = provider_host
        self.progress_callback = progress_callback

    def setProgressCallback(self, progress_callback):
        self.progress_callback = progress_callback

    def load(self, url):
        # read from internet
        # TODO: check callback and timeout
        blocksize = 4096
        if self.progress_callback:
            self.progress_callback(0)
        fd = urlopen(url)
        idata = fd.read(blocksize)
        loaded = blocksize
        while True:
            bdata = fd.read(blocksize)
            if not bdata:
                break
            loaded += blocksize
            if self.progress_callback:
                self.progress_callback(loaded)
            idata += bdata
        fd.close()
        if self.progress_callback:
            self.progress_callback(-1)
        return idata

    def get(self):
        """
        Downloads geojson and parse geometries, BBOX is ignored
        TODO: clustering
        """

        # geojson URL is in the provider_host
        url = self.provider_host
        if not url:
            return None

        key = hashlib.md5(url).hexdigest()
        if key in self.cache:
            return self.cache[key]

        try:
            gj = json.loads(self.load(url))
            # GET EPSG CRS
            crs_desc = gj.get('crs').get('properties').get('href')
            match = re.search(r'epsg/([^/]+)', crs_desc)
            srs = 'EPSG:' + match.groups()[0]
            # FIXME: didn't understand what customBounds is for
            self.customBounds = None
            self.isPGoogle = False
            self.isPLatLon = False
            if srs=="EPSG:4326":
                self.isPLatLon = True
            elif srs=="EPSG:900913" or srs == "EPSG:3857":
                self.isPGoogle = True
                try:
                    self.projection = pGoogle
                except:
                    pass
            else:
                try:
                    self.projection = Proj(init=srs)
                except:
                    pass
            self.geometries = gj.get('features')
            self.cache[key] = self.geometries
            return self.geometries
            
        except Exception, e:
            Logger.error('OverlayServer could not find (or read) GEOJSON from %s [%s]'
                          % (url, e))

    def getInfoText(self, member):
        fields = member.getchildren()[0].getchildren()
        info = ''
        for field in fields:
            if field.text is not None and field.text.strip() != '':
                info += '%s: %s\n' % (field.tag[field.tag.index('}')
                        + 1:], field.text)
        return info

    def getInfo(self, lat, lon, epsilon, ):
        """
        Return clicked feature
        TODO: implementation
        """
        return None
        

    def xy_to_co(self, lat, lon):
        if self.customBounds:
            (x, y) = latlon_to_custom(lat, lon, self.bounds)
        elif self.isPLatLon:

                             # patch for android - does not require pyproj library

            (x, y) = (lon, lat)
        elif self.isPGoogle:

                           # patch for android - does not require pyproj library

            (x, y) = latlon_to_google(lat, lon)
        else:
            (x, y) = transform(pLatlon, self.projection, lon, lat)
        return (x, y)

    def co_to_ll(self, x, y):
        if self.customBounds:
            (l, m) = custom_to_latlon(x, y, self.bounds)
        elif self.isPLatLon:

                             # patch for android - does not require pyproj library

            (l, m) = (y, x)
        elif self.isPGoogle:

                           # patch for android - does not require pyproj library

            (l, m) = google_to_latlon(y, x)
        else:
            (l, m) = transform(self.projection, pLatlon, y, x)
        return (l, m)


