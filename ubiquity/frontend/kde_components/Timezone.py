# -*- coding: utf-8 -*-

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import datetime
import ubiquity.tz

#contains information about a geographical timezone city
class City:
    def __init__(self, cName, zName, lat, lng, zone, raw_zone):
        self.city_name = cName
        self.zone_name = zName
        self.lat = lat
        self.long = lng
        self.zone = zone
        # pre-split zone text
        self.raw_zone = raw_zone
    
class TimezoneMap(QWidget):
    def __init__(self, frontend):
        QWidget.__init__(self, frontend.userinterface.map_frame)
        self.frontend = frontend
        #load the timezones from database
        self.tzdb = ubiquity.tz.Database()
        #dictionary of zone name -> comboIndex
        self.zones = {}
        self.selected_city = None
        # list of cities indexable by the hour
        self.cities = [[] for i in range (0, 25)]
        
        self.setObjectName("timezone_map")
        
        #load main pixmap
        self.imagePath = "/usr/share/ubiquity/pixmaps"
        self.pixmap = QPixmap("%s/time_zones_background.png" % self.imagePath)
        
        self.timer = QTimer(self)
        self.frontend.app.connect(self.timer, SIGNAL("timeout()"), self.update)
        self.timer.start(1000)
        
        # zonenum + 11 = index (because I can't negative index, but the files go negative)
        self.zonePixmaps = {}
        for zone in range (-11, 13):
            self.zonePixmaps[zone + 11] = QPixmap('%s/time_zones_highlight_%d.png' % (self.imagePath, zone))
            
        for location in self.tzdb.locations:
            zone_bits = location.zone.split('/')
            
            if len(zone_bits) == 1:
                continue
            
            zoneName = zone_bits[0]
            #join the possible city names for the subregion
            #and replace the _ for a space
            cityName = '/'.join(zone_bits[1:]).replace('_', ' ')
            
            # zone is the hours offset from 0
            # adding 1800 to make the hour round correctly (round up) for non hour zones)
            zone = (location.utc_offset.seconds + 1800)//3600 + location.utc_offset.days * 24

            # FIXME, some locations give a 14 hour ahead time...im lost what does it mean??
            # hour gives one part of the story, need to get city to know what zone we have
            if zone > 13:
                zone = zone - 24
            
            if not self.zones.has_key(zoneName):
                self.zones[zoneName] = {'cities' : [], 'cindex': 0}    
            
            #make new city, and add it to the hour index
            city = City(cityName, zoneName, location.latitude, location.longitude, zone, location.zone)
            self.cities[zone+11].append(city)
            
            #also add the city to the zone
            self.zones[zoneName]['cities'].append(city)
       
        #connect combo boxes
        self.frontend.app.connect(self.frontend.userinterface.timezone_zone_combo, 
            SIGNAL("currentIndexChanged(QString)"), self.regionChanged)
        self.frontend.app.connect(self.frontend.userinterface.timezone_city_combo, 
            SIGNAL("currentIndexChanged(int)"), self.cityChanged)
            
        # zone needs to be added to combo box
        keys = self.zones.keys()
        keys.sort()
        for z in keys:
            self.zones[z]['cindex'] = self.frontend.userinterface.timezone_zone_combo.count()
            self.frontend.userinterface.timezone_zone_combo.addItem(z)
       
    # called when the region changes
    def regionChanged(self, region):
        #update the cities combo
        self.frontend.userinterface.timezone_city_combo.clear()
        #blank entry first
        self.frontend.userinterface.timezone_city_combo.addItem("")
        
        for c in self.zones[str(region)]['cities']:
            self.frontend.userinterface.timezone_city_combo.addItem(c.city_name, QVariant(c))
            
    # called when the city changes
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
            painter.drawPixmap(self.rect(), self.zonePixmaps[c.zone + 11])
            
            painter.drawLine(cpos + QPoint(1,1), cpos - QPoint(1,1))
            painter.drawLine(cpos + QPoint(1,-1), cpos - QPoint(1,-1))
            #painter.drawText(cpos + QPoint(2,-2), c.city_name)
            
            # paint the time instead of the name
            now = datetime.datetime.now(ubiquity.tz.SystemTzInfo(c.raw_zone))
            painter.drawText(cpos + QPoint(2,-2), now.strftime('%X'))
            
        #debug info for making sure the cities are in proper places
        '''for c in self.cities[-5 + 11]:
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
        
        return QPoint(int(x), int(y))
        
    def mouseReleaseEvent(self, mouseEvent):
        selected_zone = -1
        
        pos = mouseEvent.pos()
        #rescale mouse coords to have proper x/y position on unscaled image
        x = int(pos.x() * self.pixmap.width()/self.width())
        y = int(pos.y() * self.pixmap.height()/self.height())
        
        #get the zone we clicked on by checking the alpha of the pixel
        for i in range (0, 25):
            if self.zonePixmaps[i].toImage().pixel(x, y) > 0:
                selected_zone = i - 11
                break
                
        if selected_zone == -1:
            return
            
        # get closest city in the selected zone offset
        # ignore other cities in the broader zone
        closest = None
        bestdist = 0
        for c in self.cities[selected_zone + 11]:
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
            
            i = 0
            for city in self.zones[closest.zone_name]['cities']:
                if city == closest:
                    break
                i = i+1
                
            self.frontend.userinterface.timezone_city_combo.setCurrentIndex(i + 1)
            
            
        
        #old_closest = self.selected_city
        #if closest != None and self.selected_city != closest:
        #    self.selected_city = closest
            
        
        #if (oldoff != self.selected_zone_offset):
            #change the region combo
            #self.frontend.userinterface.timezone_zone_combo.setCurrentIndex()
            #self.emit(SIGNAL("cityChanged"), ())
        #self.repaint()

    def set_city_text(self, name):
        """ Gets a long name, Europe/London """
        '''
        timezone_city_combo = self.frontend.userinterface.timezone_city_combo
        count = timezone_city_combo.count()
        found = False
        i = 0
        zone_bits = name.split('/')
        human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
        while not found and i < count:
            if str(timezone_city_combo.itemText(i)) == human_zone:
                timezone_city_combo.setCurrentIndex(i)
                found = True
            i += 1'''

    def set_zone_text(self, location):
        '''offset = location.utc_offset
        if offset >= datetime.timedelta(0):
            minuteoffset = int(offset.seconds / 60)
        else:
            minuteoffset = int(offset.seconds / 60 - 1440)
        if location.zone_letters == 'GMT':
            text = location.zone_letters
        else:
            text = "%s (GMT%+d:%02d)" % (location.zone_letters,
                                         minuteoffset / 60, minuteoffset % 60)
        self.frontend.userinterface.timezone_zone_text.setText(text)
        translations = gettext.translation('iso_3166',
                                           languages=[self.frontend.locale],
                                           fallback=True)
        self.frontend.userinterface.timezone_country_text.setText(translations.ugettext(location.human_country))
        self.update_current_time()'''

    def update_current_time(self):
        '''if self.location_selected is not None:
            try:
                now = datetime.datetime.now(self.location_selected.info)
                self.frontend.userinterface.timezone_time_text.setText(unicode(now.strftime('%X'), "utf-8"))
            except ValueError:
                # Some versions of Python have problems with clocks set
                # before the epoch (http://python.org/sf/1646728).
                self.frontend.userinterface.timezone_time_text.setText('<clock error>')'''

    def set_tz_from_name(self, name):
        """ Gets a long name, Europe/London """
        '''
        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)
        self.frontend.allow_go_forward(True)

        if name == None or name == "":
            return'''

    def get_tz_from_name(self, name):
        '''if len(name) != 0 and name in self.timezone_city_index:
            return self.timezone_city_index[name]
        else:
            return None'''

    def city_combo_changed(self, index):
        '''city = str(self.frontend.userinterface.timezone_city_combo.currentText())
        try:
            zone = self.timezone_city_index[city]
        except KeyError:
            return
        self.set_tz_from_name(zone)'''

    def get_selected_tz_name(self):
        '''name = str(self.frontend.userinterface.timezone_city_combo.currentText())
        return self.get_tz_from_name(name)'''

    def timeout(self):
        '''self.update_current_time()
        return True'''

    def mapped(self):
        '''if self.update_timeout is None:
            self.update_timeout = QTimer()
            self.frontend.app.connect(self.update_timeout, SIGNAL("timeout()"), self.timeout)
            self.update_timeout.start(100)'''