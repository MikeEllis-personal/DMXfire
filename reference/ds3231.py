# ds3231_port.py Portable driver for DS3231 precison real time clock.
# Adapted from WiPy driver at https://github.com/scudderfish/uDS3231

# Author: Peter Hinch modified by Mike Ellis
# Copyright Peter Hinch 2018 Released under the MIT license.
# Additions copyright Mike Ellis August 2020.

import utime
import machine
import sys
DS3231_I2C_ADDR = 104

class DS3231:
    """ Interface to a DS3231 connected via the I2C bus
    Includes support for reading and writing the RTC, Alarm1, and Alarm2, and configuring the alarm interrupt
    or squarewave output.
    The DS3231 will be configured to operate in 24-hour mode.
    No timezone conversions will be applied.

    May throw a "DS3231 not found" runtime error if no DS3231 is present when created.

    """
    def __init__(self, i2c):
        self.ds3231 = i2c
        if DS3231_I2C_ADDR not in self.ds3231.scan():
            raise RuntimeError("DS3231 not found on I2C bus at %d" % DS3231_I2C_ADDR)

    # -------------------------------------------------------------------------------------
    def __repr__(self):
        '''Returns representation of the object'''
        return("{}({!r})".format(self.__class__.__name__, self.ds3231))

    # -------------------------------------------------------------------------------------
    @staticmethod
    def bcd2dec(bcd):
        """ Convert a BCD-encoded value in the range 0-99 to its decimal equivalent

        Args:
            bcd (int): The number to convert from BCD - valid range 0...99 (BCD)

        Returns:
            int: The decimal-equivalent of the original value
        """
        return (((int(bcd) & 0xf0) >> 4) * 10 + (int(bcd) & 0x0f))

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dec2bcd(dec):
        """ Convert a decimal value in the range 0-99 to its BCD equivalent

        Args:
            dec (int): The number to convert from decimal - valid range 0...99

        Returns:
            int: The BCD-equivalent of the original value        
        """
        try:
            tens, units = divmod(int(dec), 10)
        except Exception as e:
            sys.print_exception(e)
            print("While converting decimal = {}".format(dec))
        return (tens << 4) + units

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dayofyear(fullyear, month, day):
        """ Calculate the daye of week and day of year for a given date

        Args:
            fullyear  (int): Range 1900-2099
            month     (int): Range 1-12
            day       (int): Range 1-31

        Returns:
            Day of Year (1..366, 1 = Jan 1st)
        """
        # Use a well known congruence to determine the day of year
        n1  = (275 * month) // 9                       # Approx DOY for LAST day of the month
        n2  = (month + 9)   // 12                      # 0 for Jan/Feb, otherwise 1
        n3  = 1 + (fullyear - 4*(fullyear//4) + 2)//3  # 1 for leap years, otherwise 2
        doy = n1 - (n2 * n3) + day - 30                # Apply all the correction factors

        return doy

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dayofweek(fullyear, month, day):
        """ Calculate the daye of week and day of year for a given date

        Args:
            fullyear  (int): Range 1900-2099
            month     (int): Range 1-12
            day       (int): Range 1-31

        Returns:
            Day of Week (1..7, 1 = Sunday)
        """
        # Calculate constants for Zellers formula for day of week
        zmonth = month - 2
        if zmonth < 1:
            zmonth   += 12
            fullyear -= 1
        zcentury = fullyear // 100
        zyear    = fullyear % 100
        dow      = 1 + (day + (13*zmonth - 1)//5 - 2*zcentury + zyear + zyear//4 + zcentury//4) % 7

        return dow

    # -------------------------------------------------------------------------------------
    @staticmethod
    def is_dst_from_UTCtm(tm):
        """ Take a TM time structure and work out whether DST shoudl be applied to it

        Args:
            tm (tm): A time and date in TM format

        Returns:
            Boolean: True if the time/date is within the +1hr DST window (01:00 UTC on last Sunday in March until last Sunday in October)
        """        
        year  = tm[0]
        month = tm[1]
        mday  = tm[2]
        hour  = tm[3]

        # Handle the easy cases first
        if month < 3 or month > 10:    # Jan, Feb, Nov, Dec
            return False # Never DST

        if month > 3 and month < 10:   # Apr, May, Jun, Jul, Aug, Sep
            return True # Always DST

        # Now handle complex months - March and October

        # What day of week is the last day of the month?
        dow = DS3231.dayofweek(year, month, 31)

        # Therefore which day of the month does the change happen on?
        change_happens_on = 32 - dow

        if mday > change_happens_on:   # Change has already happened
            return month == 3            # It is DST afterwards in March, it isn't in October
        elif mday < change_happens_on: # Change hasn't already happened
            return month == 10           # It is DST before in October, it isn't in March

        # We're on the day of the change then... is it before or after 1am?
        if hour >= 1:                  # Is it after 0100 (UTC)?
            return month == 3            # It is DST afterwards in March, it isn't in October
        else:
            return month == 10           # It is DST before in October, it isn't in March

    @staticmethod
    def timegm(tm):
        """ Convert a TM tuple into a seconds-since-1970 timestamp, assuming UTC        

        Args:
            tm (tuple): Standard TM 8-tuple - DOW and DOY are ignored

        Returns:
            int: Seconds since 1st Jan 1970 00:00:00 assuming UTC
        """
        # Leading zero saves remembering that January is month 1 not month 0!
        days_in_months = (0,0,31,59,90,120,151,181,212,243,273,304,334)

        year, month, day, hour, minute, second = tm[:6]

        # How many days in the years to Jan 1st this year?
        # Magic number = 365.25 * 4, offset by 1 because 1970 wasn't a leap-year
        days = ((year - 1970) * 1461 + 1) // 4 + days_in_months[month] + day - 1
        if year % 4 == 0 and month > 2:
            days += 1  # Correct for months 3-12 in leap-years

        return 86400*days + 3600*hour + 60*minute + second 

    # -------------------------------------------------------------------------------------
    @staticmethod
    def tm_to_dsrtc(tm):
        """ Convert tm format tuple into DS3231 RTC register format
        Args:
            tm (tuple): The time in TM format - day-of-year is ignored, and day-of-week is used as given (no validation)
        Returns:
            bytearray in DS time format
        """
        ds_format = bytearray((DS3231.dec2bcd(tm[5]),        # Seconds
                               DS3231.dec2bcd(tm[4]),        # Minutes
                               DS3231.dec2bcd(tm[3]),        # Hours
                               DS3231.dec2bcd(tm[6]),        # Day of week
                               DS3231.dec2bcd(tm[2]),        # Day of month
                               DS3231.dec2bcd(tm[1]),        # Month
                               DS3231.dec2bcd(tm[0] % 100))) # Only the year within the century
        if tm[0] < 1900 or tm[0] >= 2000:
            ds_format[5] += 128 # Set the century bit (embedded in the month)        
        return ds_format

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dsrtc_to_tm(ds_format):
        """ Convert DS3231 RTC register format into tm-format
        Args:
            ds_format : bytearray(7) containing the DS format data

        Returns:
            A TM-format tuple. Day of week is as in the DS format message, and day of year is zero
        """
        second = DS3231.bcd2dec(ds_format[0])
        minute = DS3231.bcd2dec(ds_format[1])
        hour   = DS3231.bcd2dec(ds_format[2] & 0x3f) # Filter off the 12/24 bit
        #day    = DS3231.bcd2dec(ds_format[3])       # The DS3231 day of week is just a modulo 7 count - not much use, and easier to calculate
        date   = DS3231.bcd2dec(ds_format[4])
        month  = DS3231.bcd2dec(ds_format[5] & 0x1f) # Filter off the century bit
        year   = DS3231.bcd2dec(ds_format[6]) + 1900 # Assume 1900-1999

        if (ds_format[2] & 0x60) == 0x60:
            hour -= 8 # In 12 hour mode, and PM set, but BCD conversion will have +20, so -8

        if (ds_format[5] & 0x80) != 0:
            year += 100 # Update the year if the century bit is set

        dow = DS3231.dayofweek(year, month, date)
        doy = DS3231.dayofyear(year, month, date)

        return (year, month, date, hour, minute, second, dow, doy)

    # -------------------------------------------------------------------------------------
    @staticmethod
    def tm_to_dsal1(tm):
        """ Convert tm format tuple into DS3231 Alarm1 register format (HH:MM:SS and day/month or date)
        Args:
            tm (tuple): The alarm time in TM format - can specify day of week or date, not both. Will default to date if both are set.
        Returns:
            bytearray in DS alarm1 format
        """        
        if tm[2] == 0:
            # Day of week mode since date is outside the valid range (1-31)
            ds_format = bytearray((DS3231.dec2bcd(tm[5]),               # Seconds
                                   DS3231.dec2bcd(tm[4]),               # Minutes
                                   DS3231.dec2bcd(tm[3]),               # Hours
                                   DS3231.dec2bcd(tm[6]) + 0x40))       # Day of week and doy-of-week mode
        else:
            # Date mode since date is not zero
            ds_format = bytearray((DS3231.dec2bcd(tm[5]),               # Seconds
                                   DS3231.dec2bcd(tm[4]),               # Minutes
                                   DS3231.dec2bcd(tm[3]),               # Hours
                                   DS3231.dec2bcd(tm[2])))              # Date
        return ds_format

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dsal1_to_tm(ds_format):
        """ Convert DS3231 Alarm1 register format into tm-format
        Args:
            ds_format : bytearray(4) containing the DS format data

        Returns:
            A TM-format tuple representing the current Alarm1 setting
            
        Notes:
            If the alarm is set for a day of week: date = 0,     day = 1..7
            If the alarm is set for a date:        date = 1..31, day = 0
            Day of year is always zero
        """        
        second = DS3231.bcd2dec(ds_format[0] & 0x7f) # Filter off the alarm mask bit
        minute = DS3231.bcd2dec(ds_format[1] & 0x7f) # Filter off the alarm mask bit
        hour   = DS3231.bcd2dec(ds_format[2] & 0x3f) # Filter off the alarm mask and 12/24 bits

        if (ds_format[2] & 0x60) == 0x60:
            hour -= 8 # In 12 hour mode, and PM set, but BCD conversion will have +20, so -8

        if ds_format[3] & 0x40: 
            # Alarm in "day of week" mode
            day    = DS3231.bcd2dec(ds_format[3] & 0x0f)     # Filter off the alarm mask bit.
            date   = 0                                       # Signal that this ia DAY OF WEEK alarm
        else:
            day    = 0                                       # Signal that this is a DATE alarm
            date   = DS3231.bcd2dec(ds_format[3] & 0x3f)     # Filter off the alarm mask and day/date mode bits

        return (0, 0, date, hour, minute, second, day, 0)    # Build TM format response

    # -------------------------------------------------------------------------------------
    @staticmethod
    def tm_to_dsal2(tm):
        """ Convert tm format tuple into DS3231 Alarm 2 register format (HH:MM and day/month or date - note Alarm2 does NOT support seconds)
        Args:
            tm (tuple): The alarm time in TM format - can specify day of week or date, not both. Will default to date if both are set.
        Returns:
            bytearray in DS alarm2 format
        """        
        if tm[2] == 0:
            # Day of week mode since date is outside the valid range (1-31)
            ds_format = bytearray((DS3231.dec2bcd(tm[4]),               # Minutes
                                   DS3231.dec2bcd(tm[3]),               # Hours
                                   DS3231.dec2bcd(tm[6]) + 0x40))       # Day of week and doy-of-week mode
        else:
            # Date mode since date is not zero
            ds_format = bytearray((DS3231.dec2bcd(tm[4]),               # Minutes
                                   DS3231.dec2bcd(tm[3]),               # Hours
                                   DS3231.dec2bcd(tm[2])))              # Date
        return ds_format

    # -------------------------------------------------------------------------------------
    @staticmethod
    def dsal2_to_tm(ds_format):
        """ Convert DS3231 Alarm 2 register format into tm-format
        Args:
            ds_format : bytearray(3) containing the DS format data

        Returns:
            A TM-format tuple representing the current Alarm1 setting
            
        Notes:
            If the alarm is set for a day of week: date = 0,     day = 1..7
            If the alarm is set for a date:        date = 1..31, day = 0
            Day of year is always zero
        """        
        second = 0
        minute = DS3231.bcd2dec(ds_format[0] & 0x7f) # Filter off the alarm mask bit
        hour   = DS3231.bcd2dec(ds_format[1] & 0x3f) # Filter off the alarm mask and 12/24 bits

        if (ds_format[1] & 0x60) == 0x60:
            hour -= 8 # In 12 hour mode, and PM set, but BCD conversion will have +20, so -8

        if ds_format[2] & 0x40: 
            # Alarm in "day of week" mode
            day    = DS3231.bcd2dec(ds_format[2] & 0x0f)     # Filter off the alarm mask bit.
            date   = 0                                       # Signal that this ia DAY OF WEEK alarm
        else:
            day    = 0                                       # Signal that this is a DATE alarm
            date   = DS3231.bcd2dec(ds_format[2] & 0x3f)     # Filter off the alarm mask and day/date mode bits

        return (0, 0, date, hour, minute, second, day, 0)    # Build TM format response

    # -------------------------------------------------------------------------------------
    def read_ds3231_rtc(self):
        """ Read the RTC as a DS3231 formatted bytearray for addresses 0-6 inclusive
        """    
        buffer = bytearray(7)
        self.ds3231.readfrom_mem_into(DS3231_I2C_ADDR, 0, buffer)
        return buffer

    # -------------------------------------------------------------------------------------
    def read_ds3231_alarm1(self):
        """ Read Alarm1 as a DS3231 formatted bytearray for addresses 7-10 inclusive, including all Alarm Mask bits but NOT the Alarm Interupt Enable bit
        """    
        buffer = bytearray(4)
        self.ds3231.readfrom_mem_into(DS3231_I2C_ADDR, 7, buffer)
        return buffer

    # -------------------------------------------------------------------------------------
    def read_ds3231_alarm2(self):
        """ Read Alarm2 as formatted bytearray for addresses 11-13 inclusive, including all Alarm Mask bits but NOT the Alarm Interupt Enable bit
        """    
        buffer = bytearray(3)
        self.ds3231.readfrom_mem_into(DS3231_I2C_ADDR, 11, buffer)
        return buffer

    # -------------------------------------------------------------------------------------
    @property
    def rtc_tod_tm(self):
        """ Read the DS3231 RTC and return the time as a TM tuple in UK LOCAL TIME
        """
        return utime.gmtime(self.rtc_tod) # The only library function which works!

    # -------------------------------------------------------------------------------------
    @property
    def rtc_tod(self):
        """ Read the DS3231 RTC and return the time as a seconds count in UK LOCAL TIME
        """
        now     = self.rtc_tm
        to_secs = DS3231.timegm(now)

        if DS3231.is_dst_from_UTCtm(now):
            to_secs += 3600 # Add one hour
        
        return to_secs

    # -------------------------------------------------------------------------------------
    @property
    def rtc(self):
        """ Read the DS3231 RTC and return the time as seconds since midnight
        """
        return DS3231.timegm(self.rtc_tm)

    # -------------------------------------------------------------------------------------
    @rtc.setter
    def rtc(self, time_to_set):
        """ Set the DS3231 RTC

        Args:
            time_to_set (number): Seconds since epoch
        """
        self.rtc_tm = utime.gmtime(time_to_set)

    # -------------------------------------------------------------------------------------
    @property
    def rtc_tm(self):
        """ Read the DS3231 RTC and return the time as a tm tuple
        """
        return DS3231.dsrtc_to_tm(self.read_ds3231_rtc())

    # -------------------------------------------------------------------------------------
    @rtc_tm.setter
    def rtc_tm(self, time_to_set):
        """ Set the DS3231 RTC from a tm struct

        Args:
            time_to_set (tuple): Time to set as a tm tuple
        """
        self.ds3231.writeto_mem(DS3231_I2C_ADDR, 0, DS3231.tm_to_dsrtc(time_to_set))

    # -------------------------------------------------------------------------------------
    @property
    def alarm1(self):
        """ Read the DS3231 Alarm1 and return the time as seconds since epoch
        """
        tm = self.alarm1_tm
        return tm[3] * 3600 + tm[4] * 60 + tm[5]

    # -------------------------------------------------------------------------------------
    @alarm1.setter
    def alarm1(self, time_to_set):
        """ Set the DS3231 Alarm1

        Args:
            time_to_set (number): Seconds since epoch

        Notes:
            Only the hours, minutes and seconds are set in this - day and date are ignored
        """
        self.alarm1_tm = (0, 0, 0, (time_to_set // 3600) % 24, (time_to_set // 60) % 60, time_to_set % 60, 0, 0)
        #self.alarm1_tm = utime.localtime(time_to_set)

    # -------------------------------------------------------------------------------------
    @property
    def alarm1_tm(self):
        """ Read the DS3231 RTC and return the time as a tm tuple

        Returns:
            tuple: Standard tm date tuple
            
        Note:
            AL1 only has Day/Date:HH:MM:SS fields. YY and MON will therefore always be zero.
            If the DS AL1 is in Date mode, then Date will be in the range 1-31 and Day will be 0.
            if the DS AL1 is in Day of Week mode, then Date will be 0 Day will be in the range 0-6.
        """
        return DS3231.dsal1_to_tm(self.read_ds3231_alarm1())

    # -------------------------------------------------------------------------------------
    @alarm1_tm.setter
    def alarm1_tm(self, time_to_set):
        """ Set the DS3231 RTC to the tm tuple given

        Args:
            time_to_set (tuple): The standard tm tuple description of the desired alarm time. 
        
        Notes:
            AL1 only uses Day/Date:HH:MM:SS fields. 
            If Date=0 then Day mode is used, otherwise the date mode is used.
            The alarm interrupt will be set to "precise match" - i.e. Day/Date, HH:MM:SS must match exactly.
            The alarm interrupt enable will not be altered.        
        """
        #print("AL1 set to    : {}".format(time_to_set))
        self.ds3231.writeto_mem(DS3231_I2C_ADDR, 7, DS3231.tm_to_dsal1(time_to_set))
    # -------------------------------------------------------------------------------------
    @property
    def alarm2(self):
        """ Read the DS3231 Alarm1 and return the time as seconds since epoch
        """
        tm = self.alarm2_tm
        return tm[3] * 3600 + tm[4] * 60 + tm[5]

    # -------------------------------------------------------------------------------------
    @alarm2.setter
    def alarm2(self, time_to_set):
        """ Set the DS3231 Alarm1

        Args:
            time_to_set (number): Seconds since epoch

        Notes:
            Only the hours, minutes and seconds are set in this - day and date are ignored
        """
        self.alarm2_tm = (0, 0, 0, (time_to_set // 3600) % 24, (time_to_set // 60) % 60, time_to_set % 60, 0, 0)
        #self.alarm1_tm = utime.localtime(time_to_set)

    # -------------------------------------------------------------------------------------
    @property
    def alarm2_tm(self):
        """ Read the DS3231 RTC and return the time as a tm tuple

        Returns:
            tuple: Standard tm date tuple
            
        Note:
            AL1 only has Day/Date:HH:MM:SS fields. YY and MON will therefore always be zero.
            If the DS AL1 is in Date mode, then Date will be in the range 1-31 and Day will be 0.
            if the DS AL1 is in Day of Week mode, then Date will be 0 Day will be in the range 0-6.
        """
        return DS3231.dsal2_to_tm(self.read_ds3231_alarm2())

    # -------------------------------------------------------------------------------------
    @alarm2_tm.setter
    def alarm2_tm(self, time_to_set):
        """ Set the DS3231 RTC to the tm tuple given

        Args:
            time_to_set (tuple): The standard tm tuple description of the desired alarm time. 
        
        Notes:
            AL2 only uses Day/Date:HH:MM fields. 
            If Date=0 then Day mode is used, otherwise the date mode is used.
            The alarm interrupt will be set to "precise match" - i.e. Day/Date, HH:MM:SS must match exactly.
            The alarm interrupt enable will not be altered.        
        """
        self.ds3231.writeto_mem(DS3231_I2C_ADDR, 11, DS3231.tm_to_dsal2(time_to_set))

    # -------------------------------------------------------------------------------------
    @property
    def cal(self):
        """ Read the DS3231 calibration factor and return as an integer

        Returns:
            integer: Current calibration factor in the range -128 to +127
            
        """
        buffer = bytearray(1)
        self.ds3231.readfrom_mem_into(DS3231_I2C_ADDR, 0x10, buffer)

        # Handle conversion from unsigned byte to integer
        if buffer[0] <= 127:
            return buffer[0]
        else:
            return buffer[0]-256

    # -------------------------------------------------------------------------------------
    @cal.setter
    def cal(self, cal_to_set):
        """ Set the DS3231 calibration factor

        Args:
            time_to_set (tuple): The standard tm tuple description of the desired alarm time. 
        
        Notes:
            AL1 only uses Day/Date:HH:MM:SS fields. 
            If Date=0 then Day mode is used, otherwise the date mode is used.
            The alarm interrupt will be set to "precise match" - i.e. Day/Date, HH:MM:SS must match exactly.
            The alarm interrupt enable will not be altered.        
        """
        buffer = bytearray(1)
        buffer[0] = cal_to_set # Automatically handles negative numbers as two's complement
        self.ds3231.writeto_mem(DS3231_I2C_ADDR, 0x10, buffer)

    # -------------------------------------------------------------------------------------
    @property
    def temp(self):
        """ Read the DS3231 temperature sensor

        Returns:
            number: Current temperature in Celsius, with quarter-degree resolution
            
        """
        buffer = bytearray(2)
        self.ds3231.readfrom_mem_into(DS3231_I2C_ADDR, 0x11, buffer)

        temp = (buffer[0] & 0x7f) + ((buffer[1] >> 6) / 4.0)
        if buffer[0] & 0x80:
            return -temp
        else:
            return temp
