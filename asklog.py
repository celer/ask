#------------------------------------------------------------------------------
#	asklog.py - log related functions
#
#	(C) 2001-2006 by Marco Paganini (paganini@paganini.net)
#
#   This file is part of ASK - Active Spam Killer
#
#   ASK is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   ASK is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with ASK; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	$Id: asklog.py,v 1.9 2006/01/09 04:22:26 paganini Exp $
#------------------------------------------------------------------------------

import time
import os

#------------------------------------------------------------------------------

class AskLog:
	"""
	Logs the output.

	Variables:
	
	- level:   global log level
	- outfile: output filename
	- logfh:   file object pointing to the logfile
	"""

	outfile   = ""
	loglevel  = 0
	
	#------------------------------------------------------------------------------
	def __init__(self, outfile):
		"""
		Initializes the AskLog class. 'outfile' should point to the
		desired filename (will be opened in 'append' mode).
		"""

		if (outfile != ''):
			self.outfile = outfile;
			self.logfh   = open(outfile, "a")

	#------------------------------------------------------------------------------
	def __del__(self):
		## If no logging exist, logfh will not be valid
		try:
			self.logfh.close()
		except:
			pass

	#------------------------------------------------------------------------------
	def write(self, level, str):
		"Generate a log output if self.loglevel >= level and outfile is not null"

		if (self.loglevel >= level and self.outfile != ''):
			self.logfh.write("%s [%s]: %s\n" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(time.time())), os.getpid(), str))
			self.logfh.flush()

## EOF ##
