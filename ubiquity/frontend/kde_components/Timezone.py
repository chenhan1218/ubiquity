# -*- coding: utf-8 -*-

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import datetime
import ubiquity.tz

#contains information about a geographical timezone city
class City:
    def __init__(self, cName, zName, lat, lng, raw_zone):
        self.city_name = cName
        self.zone_name = zName
        self.lat = lat
        self.long = lng
        self.pixmap = None
        # pre-split zone text
        self.raw_zone = raw_zone
        #index in the cities array
        self.index = 0
    
class TimezoneMap(QWidget):
    def __init__(self, frontend):
        QWidget.__init__(self, frontend.userinterface.map_frame)
        self.frontend = frontend
        #dictionary of zone name -> {'cindex', 'citites'}
        self.zones = {}
        # currently active city
        self.selected_city = None
        #dictionary of full name (ie. 'Australia/Sydney') -> city
        self.cities = {}
        self.setObjectName("timezone_map")
        
        #load background pixmap
        self.imagePath = "/usr/share/ubiquity/pixmaps/timezone"
        self.pixmap = QPixmap("%s/bg.png" % self.imagePath)
        
        #redraw timer for selected city time
        self.timer = QTimer(self)
        QApplication.instance().connect(self.timer, SIGNAL("timeout()"), self.update)
        self.timer.start(1000)
        
        #load the pixmaps for the zone overlays
        zones = ['0.0', '1.0', '2.0', '3.0', '3.5', '4.0', '4.5', '5.0', '5.75', '6.0', 
            '6.5', '7.0', '8.0', '9.0', '9.5', '10.0', '10.5', '11.0', '11.5', '12.0', '12.75', '13.0',
            '-1.0', '-2.0', '-3.0', '-3.5', '-4.0', '-5.0', '-5.5', '-6.0', '-7.0', 
            '-8.0', '-9.0', '-9.5', '-10.0', '-11.0']
            
        zonePixmaps = {}
            
        for zone in zones:
            #print '%s/timezone_%s.png' % (self.imagePath, zone)
            zonePixmaps[zone] = QPixmap('%s/timezone_%s.png' % (self.imagePath, zone));
            
        #load the timezones from database
        tzdb = ubiquity.tz.Database()
        for location in tzdb.locations:
            zone_bits = location.zone.split('/')
            
            if len(zone_bits) == 1:
                continue
            
            zoneName = zone_bits[0]
            #join the possible city names for the subregion
            #and replace the _ for a space
            cityName = '/'.join(zone_bits[1:]).replace('_', ' ')
            
            # zone is the hours offset from 0
            zoneHour = (location.utc_offset.seconds)/3600.0 + location.utc_offset.days * 25
            
            #wrap around
            if zoneHour > 13.0:
                zoneHour -= 24.0
            
            # add the zone if we don't have t already listed
            if not self.zones.has_key(zoneName):
                self.zones[zoneName] = {'cities' : [], 'cindex': 0}    
            
            #make new city
            city = City(cityName, zoneName, location.latitude, location.longitude, location.zone)
            
            #set the pixamp to show for the city
            zoneS = str(zoneHour)
            
            #try to find the closest zone
            if not zonePixmaps.has_key(zoneS):
                if zonePixmaps.has_key(str(zoneHour + .25)):
                    zoneS = str(zoneHour + .25)
                elif zonePixmaps.has_key(str(zoneHour + .25)):
                    zoneS = str(zoneHour - .25)
                elif zonePixmaps.has_key(str(zoneHour + .5)):
                    zoneS = str(zoneHour + .5)
                elif zonePixmaps.has_key(str(zoneHour - .5)):
                    zoneS = str(zoneHour - .5)
                else:
                    #no zone...default to nothing
                    zoneS = None
                
            if zoneS:
                city.pixmap = zonePixmaps[zoneS]
            
            self.cities[location.zone] = city
            
            # add the city to the zone list
            city.index = len(self.zones[zoneName]['cities'])
            self.zones[zoneName]['cities'].append(city)
       
        QApplication.instance().connect(self.frontend.userinterface.timezone_zone_combo, 
            SIGNAL("currentIndexChanged(QString)"), self.regionChanged)
        QApplication.instance().connect(self.frontend.userinterface.timezone_city_combo, 
            SIGNAL("currentIndexChanged(int)"), self.cityChanged)
            
        # zone needs to be added to combo box
        keys = self.zones.keys()
        keys.sort()
        for z in keys:
            self.zones[z]['cindex'] = self.frontend.userinterface.timezone_zone_combo.count()
            self.frontend.userinterface.timezone_zone_combo.addItem(z)
       
    # called when the region(zone) combo changes
    def regionChanged(self, region):
        self.frontend.userinterface.timezone_city_combo.clear()
        #blank entry first to prevent a city from being selected
        self.frontend.userinterface.timezone_city_combo.addItem("")
        
        #add all the cities
        for c in self.zones[str(region)]['cities']:
            self.frontend.userinterface.timezone_city_combo.addItem(c.city_name, QVariant(c))
            
    # called when the city combo changes
    def cityChanged(self, cityindex):
        if cityindex < 1:
            return
            
        city = self.frontend.userinterface.timezone_city_combo.itemData(cityindex).toPyObject()
        self.selected_city = city
        self.repaint()
       
    def paintEvent(self, paintEvent):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.pixmap)
        
        if self.selected_city != None:
            c = self.selected_city
            cpos = self.getPosition(c.lat, c.long)
            
            if (c.pixmap):
                painter.drawPixmap(self.rect(), c.pixmap)
            
            painter.drawLine(cpos + QPoint(1,1), cpos - QPoint(1,1))
            painter.drawLine(cpos + QPoint(1,-1), cpos - QPoint(1,-1))
            #painter.drawText(cpos + QPoint(2,-2), c.city_name)
            
            # paint the time instead of the name
            try:
                now = datetime.datetime.now(ubiquity.tz.SystemTzInfo(c.raw_zone))
                timestring = now.strftime('%X')
                
                text_offset = QPoint(2,-2)
            
                # correct the text render position if text will render off widget
                text_size = painter.fontMetrics().size(Qt.TextSingleLine, timestring)
                if cpos.x() + text_size.width() > self.width():
                    text_offset.setX(-text_size.width() - 2)
                if cpos.y() - text_size.height() < 0:
                    text_offset.setY(text_size.height() - 2)
                
                painter.drawText(cpos + text_offset, timestring)
            except ValueError:
                # Some versions of Python have problems with clocks set
                # before the epoch (http://python.org/sf/1646728).
                # ignore and don't display a string
                pass
            
        #debug info for making sure the cities are in proper places
        '''for c in self.zones['America']['cities']:
            cpos = self.getPosition(c.lat, c.long)
            
            painter.drawLine(cpos + QPoint(1,1), cpos - QPoint(1,1))
            painter.drawLine(cpos + QPoint(1,-1), cpos - QPoint(1,-1))
            #painter.drawText(cpos + QPoint(2,-2), c.city_name)'''
        
    # @return pixel coordinate of a latitude and longitude for self
    def getPosition(self, la, lo):
        # need to add/sub magic numbers because the map doesn't actually go from -180...180, -90...90
        # thus the upper corner is not -180, -90 and we have to compensate
        # we need a better method of determining the actually range so we can better place citites (shtylman)
        xdeg_offset = -6
        ydeg_offset = 8
        # the 180 - 35) accounts for the fact that the map does not span the entire -90 to 90
        # the map does span the entire 360 though, just offset
        x = (self.width() * (180.0 + lo) / 360.0) + (self.width() * xdeg_offset/ 180.0)
        y = (self.height() * (90.0 - la) / (180.0 - 35)) + (self.height() * ydeg_offset / (180 - 35))
        
        # this keeps the coordinate on the widget because the map wraps
        y = y % self.height()
        x = x % self.width()
        
        return QPoint(int(x), int(y))
        
    def mouseReleaseEvent(self, mouseEvent):
        selected_zone = -1
        
        pos = mouseEvent.pos()
        #rescale mouse coords to have proper x/y position on unscaled image
        x = int(pos.x() * self.pixmap.width()/self.width())
        y = int(pos.y() * self.pixmap.height()/self.height())
        
        # get closest city to the point clicked
        closest = None
        bestdist = 0
        for z in self.zones.values():
            for c in z['cities']:
                np = pos - self.getPosition(c.lat, c.long)
                dist = np.x() * np.x() + np.y() * np.y()
                if (dist < bestdist or closest == None):
                    closest = c
                    bestdist = dist
                    continue
        
        #we need to set the combo boxes
        #this will cause the redraw we need
        if closest != None:
            cindex = self.zones[closest.zone_name]['cindex']
            self.frontend.userinterface.timezone_zone_combo.setCurrentIndex(cindex)
            self.frontend.userinterface.timezone_city_combo.setCurrentIndex(closest.index + 1)

    # sets the timezone based on the full name (i.e 'Australia/Sydney')
    def set_timezone(self, name):
        self._set_timezone(self.cities[name])
    
    # internal set timezone based on a city
    def _set_timezone(self, city):
        cindex = self.zones[city.zone_name]['cindex']
        self.frontend.userinterface.timezone_zone_combo.setCurrentIndex(cindex)
        self.frontend.userinterface.timezone_city_combo.setCurrentIndex(city.index + 1)

    # return the full timezone string
    def get_timezone(self):
        if self.selected_city == None:
            return None
        
        return self.selected_city.raw_zone
