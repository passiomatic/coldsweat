"""	TimeFormat
	--------------------------------------------------------------------
	Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
	All rights reserved.
	
	Redistribution and use in source and binary forms, with or without
	modification, are permitted provided that the following conditions
	are met:
	1. Redistributions of source code must retain the above copyright
	   notice, this list of conditions and the following disclaimer.
	2. Redistributions in binary form must reproduce the above copyright
	   notice, this list of conditions and the following disclaimer in the
	   documentation and/or other materials provided with the distribution.
	3. The name of the author may not be used to endorse or promote products
	   derived from this software without specific prior written permission.
	
	THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
	IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
	OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
	IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
	INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
	NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
	DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
	THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
	(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
	THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import re, time, locale, string, math, os

__version__ = "1.1.0"

goodLocaleModule = 1
for attribute in ['DAY_1', 'ABDAY_1', 'MON_1', 'ABMON_1', 'nl_langinfo']:
	if (not hasattr (locale, attribute)):
		goodLocaleModule = 0

# We only use this alternative locale implementation if we have to.
class alternativeLocale:
	def __init__ (self):
		self.__counter__ = 0
		self.__lookupMap__ = {}
		self.__getDays__ ()
		self.__getMonths__ ()
		
	def nl_langinfo (self, aconstant):
		return self.__lookupMap__ (aconstant)
		
	def __getDays__ (self):
		# The reference date we use to build up the locale data
		# The 24th of May 2004 was a Monday
		refDate = [2004,5,24, 00, 00, 00, 0, 146, 0]
		day_keys = []
		abday_keys = []
		for weekDay in range (0,7):
			# Get the long and the short locale for this day
			longDay = time.strftime ('%A', refDate)
			shortDay = time.strftime ('%a', refDate)
			
			self.__lookupMap__ [self.__counter__] = longDay
			day_keys.append (self.__counter__)
			self.__counter__ = self.__counter__ + 1
			
			self.__lookupMap__ [self.__counter__] = shortDay
			abday_keys.append (self.__counter__)
			self.__counter__ = self.__counter__ + 1
			
			# Move on to the next day
			refDate [2] = refDate [2] + 1
			refDate [6] = refDate [6] + 1
			refDate [7] = refDate [7] + 1
			
		# Fill out the constants at the module level
		# DAY_1 is a Sunday, so do that last.
		
		self.DAY_2 = day_keys[0]
		self.DAY_3 = day_keys[1]
		self.DAY_4 = day_keys[2]
		self.DAY_5 = day_keys[3]
		self.DAY_6 = day_keys[4]
		self.DAY_7 = day_keys[5]
		self.DAY_1 = day_keys[6]
		
		# The short day constants
		
		self.ABDAY_2 = abday_keys[0]
		self.ABDAY_3 = abday_keys[1]
		self.ABDAY_4 = abday_keys[2]
		self.ABDAY_5 = abday_keys[3]
		self.ABDAY_6 = abday_keys[4]
		self.ABDAY_7 = abday_keys[5]
		self.ABDAY_1 = abday_keys[6]
		
	def __getMonths__ (self):
		# The reference date we use to build up the locale data
		month_keys = []
		abmonth_keys = []
		for month in range (1,13):
			# Get a time module format date for this month
			refDate = time.strptime ("%s 2004" % str (month), '%m %Y')
			
			# Get the long and the short locale for this day
			longMonth = time.strftime ('%B', refDate)
			shortMonth = time.strftime ('%b', refDate)
			
			self.__lookupMap__ [self.__counter__] = longMonth
			month_keys.append (self.__counter__)
			self.__counter__ = self.__counter__ + 1
			
			self.__lookupMap__ [self.__counter__] = shortMonth
			abmonth_keys.append (self.__counter__)
			self.__counter__ = self.__counter__ + 1
			
		# Fill out the constants at the module level
		# MON_1 is January
		
		self.MON_1 = month_keys[0]
		self.MON_2 = month_keys[1]
		self.MON_3 = month_keys[2]
		self.MON_4 = month_keys[3]
		self.MON_5 = month_keys[4]
		self.MON_6 = month_keys[5]
		self.MON_7 = month_keys[6]
		self.MON_8 = month_keys[7]
		self.MON_9 = month_keys[8]
		self.MON_10 = month_keys[9]
		self.MON_11 = month_keys[10]
		self.MON_12 = month_keys[11]
		
		# The short constants
		self.ABMON_1 = abmonth_keys[0]
		self.ABMON_2 = abmonth_keys[1]
		self.ABMON_3 = abmonth_keys[2]
		self.ABMON_4 = abmonth_keys[3]
		self.ABMON_5 = abmonth_keys[4]
		self.ABMON_6 = abmonth_keys[5]
		self.ABMON_7 = abmonth_keys[6]
		self.ABMON_8 = abmonth_keys[7]
		self.ABMON_9 = abmonth_keys[8]
		self.ABMON_10 = abmonth_keys[9]
		self.ABMON_11 = abmonth_keys[10]
		self.ABMON_12 = abmonth_keys[11]


if (goodLocaleModule):
	localeModule = locale
else:
	# We are on Windows or some other platform with an incomplete loacle module
	localeModule = alternativeLocale ()

# Regex for our date/time format strings.  Format is: %TYPE[\[MODIFIER\]]
# %% is used to escape the %
regex = re.compile ('(%[%abcCdHIjmMnpPrStTuUwWxXyYZz])(\[[^\]]*\])?')
strftime_regex = re.compile ('((?<!%)%[mlnhkjedacbyxzutwprMIHDFACBYXZUTWPSR])')

# Used to index into locale
DAY_WEEK_LONG = [localeModule.DAY_2, localeModule.DAY_3, localeModule.DAY_4, localeModule.DAY_5, localeModule.DAY_6, localeModule.DAY_7, localeModule.DAY_1]
DAY_WEEK_SHORT = [localeModule.ABDAY_2, localeModule.ABDAY_3, localeModule.ABDAY_4, localeModule.ABDAY_5, localeModule.ABDAY_6, localeModule.ABDAY_7, localeModule.ABDAY_1]

MONTH_LONG = [localeModule.MON_1, localeModule.MON_2, localeModule.MON_3, localeModule.MON_4, localeModule.MON_5, localeModule.MON_6, localeModule.MON_7, localeModule.MON_8
				,localeModule.MON_9, localeModule.MON_10, localeModule.MON_11, localeModule.MON_12]
MONTH_SHORT = [localeModule.ABMON_1, localeModule.ABMON_2, localeModule.ABMON_3, localeModule.ABMON_4, localeModule.ABMON_5, localeModule.ABMON_6, localeModule.ABMON_7
				, localeModule.ABMON_8,localeModule.ABMON_9, localeModule.ABMON_10, localeModule.ABMON_11, localeModule.ABMON_12]
					
# Default names if locale function nl_langinfo doesn't work
DEFAULT_DAY_WEEK = {localeModule.DAY_2: 'Monday', localeModule.DAY_3: 'Tuesday', localeModule.DAY_4: 'Wednesday', localeModule.DAY_5: 'Thursday'
					,localeModule.DAY_6: 'Friday', localeModule.DAY_7: 'Saturday', localeModule.DAY_1: 'Sunday'
					,localeModule.ABDAY_2: 'Mon', localeModule.ABDAY_3: 'Tue', localeModule.ABDAY_4: 'Wed', localeModule.ABDAY_5: 'Thu'
					,localeModule.ABDAY_6: 'Fri', localeModule.ABDAY_7: 'Sat', localeModule.ABDAY_1: 'Sun'}
DEFAULT_MONTH = {localeModule.MON_1: 'January', localeModule.MON_2: 'February', localeModule.MON_3: 'March', localeModule.MON_4: 'April', localeModule.MON_5: 'May'
				,localeModule.MON_6: 'June', localeModule.MON_7: 'July', localeModule.MON_8: 'August', localeModule.MON_9: 'September', localeModule.MON_10: 'October'
				,localeModule.MON_11: 'November', localeModule.MON_12: 'December'
				,localeModule.ABMON_1: 'Jan', localeModule.ABMON_2: 'Feb', localeModule.ABMON_3: 'Mar', localeModule.ABMON_4: 'Apr', localeModule.ABMON_5: 'May'
				,localeModule.ABMON_6: 'Jun', localeModule.ABMON_7: 'Jul',localeModule.ABMON_8: 'Aug', localeModule.ABMON_9: 'Sep', localeModule.ABMON_10: 'Oct'
				,localeModule.ABMON_11: 'Nov', localeModule.ABMON_12: 'Dec'}
					
# Use this if no locale format is available.  Note this is in stfrtime format not TimeFormat
DEFAULT_T_FMT_AMPM = '%I:%M:%S %p'
DEFAULT_D_T_FMT = "%a %b %e %H:%M:%S %Y"
DEFAULT_D_FMT = "%d/%m/%Y"
DEFAULT_T_FMT = "%H:%M:%S"
					
# Used to convert strftime format into TimeFormat format.
STRFMAP = 	{'%a': '%a[SHORT]', '%A': '%a[LONG]', '%b': '%b[SHORT]', '%B': '%b[LONG]', '%c': '%c', '%C': '%C', '%d': '%d[0]'
			,'%D': '%m[0]/%d[0]/%y[0]', '%e': '%d[SP]', '%F': '%Y-%m[0]-%d[0]', '%h': '%b[SHORT]', '%H': '%H[0]', '%I': '%I[0]'
			,'%j': '%j[0]', '%k': '%H[SP]', '%l': '%I[SP]', '%m': '%m[0]', '%M': '%M[0]', '%n': '%n', '%p': '%p', '%P': '%P'
			,'%r': '%r', '%R': '%H[0]:%M[0]', '%S': '%S[0]', '%t': '%t', '%T': '%H[0]:%M[0]:%S[0]', '%u': '%u', '%U': '%U'
			,'%w': '%w', '%W': '%W[0]', '%x': '%x', '%X': '%X', '%y': '%y[0]', '%Y': '%Y', '%z': '%T', '%Z': '%Z'}
				
# NOT IMPLEMENTED: %E, %G, %g, %O, %s, %V

def format (informat, intime = None, utctime = 0):
	""" Python implementation of an alternative strftime format with more options.
		For %c, %p, %P, %U, %x, %X, %W we fall back to the 'C' implementation due to limitations 
		in Python's locale support.
		
		Set utctime to 1 if the time is in UTC rather than local.
	"""
	if (intime is None):
		ourTime = time.localtime()
	else:
		ourTime = intime
		
	resultBuf = []
	
	position = 0
	last = 0
	match = regex.search (informat)
	while (match):
		resultBuf.append (informat [last:match.start()])
		formatType, formatModifier = match.groups()
		if (formatType == '%a'):
			# Weekday in locale
			resultBuf.append (_getWeekday_ (ourTime[6], formatModifier))
		elif (formatType == '%b'):
			# Month in locale
			resultBuf.append (_getMonth_ (ourTime[1], formatModifier))
		elif (formatType == '%d'):
			# Month as a number
			resultBuf.append (_getNumber_ (ourTime[2], formatModifier, '[0]'))
		elif (formatType == '%H'):
			# Hour in 24 hour format 
			resultBuf.append (_getNumber_ (ourTime[3], formatModifier, '[0]'))
		elif (formatType == '%I'):
			# Hour in 12 hour  format
			hour = ourTime [3]
			if (hour == 0):
				resultBuf.append ("12")
			elif (hour > 12):
				resultBuf.append (_getNumber_ (hour - 12, formatModifier, '[0]'))
			else:
				resultBuf.append (_getNumber_ (hour, formatModifier, '[0]'))
		elif (formatType == '%j'):
			# Day of year as a number
			resultBuf.append (_getNumber_ (ourTime[7], formatModifier, '[0]', 3))
		elif (formatType == '%m'):
			# Month of year as a number
			resultBuf.append (_getNumber_ (ourTime[1], formatModifier, '[0]'))
		elif (formatType == '%M'):
			# Minute as a number
			resultBuf.append (_getNumber_ (ourTime[4], formatModifier, '[0]'))
		elif (formatType == '%n'):
			resultBuf.append (os.linesep)
		elif (formatType == '%t'):
			resultBuf.append ('\t')
		elif (formatType == '%r'):
			try:
				ampmFmt = localeModule.nl_langinfo (localeModule.T_FMT_AMPM)
			except:
				ampmFmt = DEFAULT_T_FMT_AMPM
			# Now get a translation and expansion of this.
			resultBuf.append (strftime (ampmFmt, ourTime))
		elif (formatType == '%c'):
			try:
				prefFmt = localeModule.nl_langinfo (localeModule.D_T_FMT)
			except:
				prefFmt = DEFAULT_D_T_FMT
			# Now get a translation and expansion of this.
			resultBuf.append (strftime (prefFmt, ourTime))
		elif (formatType == '%x'):
			try:
				prefFmt = localeModule.nl_langinfo (localeModule.D_FMT)
			except:
				prefFmt = DEFAULT_D_FMT
			# Now get a translation and expansion of this.
			resultBuf.append (strftime (prefFmt, ourTime))
		elif (formatType == '%X'):
			try:
				prefFmt = localeModule.nl_langinfo (localeModule.T_FMT)
			except:
				prefFmt = DEFAULT_T_FMT
			# Now get a translation and expansion of this.
			resultBuf.append (strftime (prefFmt, ourTime))
		elif (formatType == '%S'):
			# Second  as a number
			resultBuf.append (_getNumber_ (ourTime[5], formatModifier, '[0]'))
		elif (formatType == '%w'):
			# Day of week as number, Sunday = 0
			weekDayNum = ourTime [6] + 1
			if (weekDayNum == 7):
				weekDayNum = 0
			resultBuf.append (str (weekDayNum))
		elif (formatType == '%u'):
			# Day of week as number, Monday = 1
			weekDayNum = ourTime [6] + 1
			resultBuf.append (str (weekDayNum))
		elif (formatType == '%y'):
			# 2 digit year
			year = int (str (ourTime [0])[2:])
			resultBuf.append (_getNumber_ (year, formatModifier, '[0]'))
		elif (formatType == '%Y'):
			# 4 digit year
			resultBuf.append (str (ourTime [0]))
		elif (formatType == '%C'):
			# 2 digit century
			resultBuf.append (str (ourTime [0])[0:2])
		elif (formatType == '%p' or formatType == '%P'):
			# Have to fall back on the 'C' version
			resultBuf.append (time.strftime (formatType, ourTime))
		elif (formatType == '%U' or formatType == '%W'):
			# Fall back to 'C' version, but still allow the extra modifier.
			resultBuf.append (_getNumber_ (int (time.strftime (formatType, ourTime)), formatModifier, '[0]'))
		elif (formatType == '%z'):
			# W3C Timezone format
			resultBuf.append (_getTimeZone_ (w3cFormat = 1, utctime = utctime))
		elif (formatType == '%T'):
			# hhmm timezone format
			resultBuf.append (_getTimeZone_ (w3cFormat = 0, utctime = utctime))
		elif (formatType == '%Z'):
			# TLA timezone format
			if (utctime):
				resultBuf.append ('UTC')
			elif (ourTime [8] == 1):
				resultBuf.append (time.tzname[1])
			else:
				resultBuf.append (time.tzname[0])
		elif (formatType == '%%'):
			resultBuf.append ('%')
		else:
			# Silently ignore the error - print as litteral
			if (formatModifier is None):
				resultBuf.append ("%s" % formatType)
			else:
				resultBuf.append ("%s%s" % (formatType, formatModifier))
		last = match.end()
		match = regex.search (informat, last)
	resultBuf.append (informat [last:])
		
	return u"".join (resultBuf)
	
def strftime (informat, intime = None):
	""" Provides a backwards-compatible strftime implementation.
		This converts strftime format codes into TimeFormat codes, and then expands them using format()
	"""
	resultBuf = []
	
	position = 0
	last = 0
	match = strftime_regex.search (informat)
	while (match):
		resultBuf.append (informat [last:match.start()])
		formatType = match.group(1)
		if (STRFMAP.has_key (formatType)):
			resultBuf.append (STRFMAP [formatType])
		else:
			# Silently ignore the error - print as litteral
			resultBuf.append ("%s" % formatType)
		last = match.end()
		match = strftime_regex.search (informat, last)
	resultBuf.append (informat [last:])
	
	# Now expand the TimeFormat string
	return format (u"".join (resultBuf), intime)


def _getWeekday_ (dayOfWeek, formatModifier):
	constantList = DAY_WEEK_LONG
	
	if (formatModifier == '[SHORT]'):
		constantList = DAY_WEEK_SHORT
	
	localeConst = constantList [dayOfWeek]
	
	try:
		weekDay = localeModule.nl_langinfo (localeConst)
		return weekDay
	except:
		# nl_langinfo not supported
		return DEFAULT_DAY_WEEK [localeConst]
		
def _getMonth_ (monthNum, formatModifier):
	constantList = MONTH_LONG
	
	if (formatModifier == '[SHORT]'):
		constantList = MONTH_SHORT
	
	# Months are 1-12 not 0-11
	localeConst = constantList [monthNum-1]
	
	try:
		monthName = localeModule.nl_langinfo (localeConst)
		return monthName
	except:
		# nl_langinfo not supported
		return DEFAULT_MONTH [localeConst]
		
def _getNumber_ (theNumber, formatModifier, defaultModifier, cols=2):
	" Returns a positive digit number either as-is, or padded"
	if (formatModifier is None):
		formatModifier = defaultModifier
	
	# By default do no padding
	padding = 0
	
	if (formatModifier == '[NP]'):
		padding = 0
	elif (formatModifier == '[SP]'):
		padding = 1
		padder = " "
	elif (formatModifier == '[0]'):
		padding = 1
		padder = "0"
		
	if (padding == 0):
		return str (theNumber)
	
	ourNum = str (theNumber)
	
	return "%s%s" % (padder * (cols - len (ourNum)), ourNum)
	
def _getTimeZone_ (w3cFormat, utctime):
	if (utctime):
		if (w3cFormat):
			return "Z"
		return "-0000"
	
	# Work out the timezone in +/-HH:MM format.
	if (time.daylight):
		offset = time.altzone
	else:
		offset = time.timezone
	absoffset = abs (offset)
	hours = int (math.floor (absoffset/3600.0))
	mins = int (math.floor ((absoffset - (hours * 3600))/60.0))
	if (offset > 0):
		thesign = "-"
	else:
		thesign = "+"
	if (w3cFormat):
		return "%s%s:%s" % (thesign, string.zfill (hours,2), string.zfill (mins, 2))
	else:
		return "%s%s%s" % (thesign, string.zfill (hours,2), string.zfill (mins, 2))


