#------------------------------------------------------------------------------
#	askconfig.py - configuration related functions
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
#	$Id: askconfig.py,v 1.59 2006/01/09 04:22:26 paganini Exp $
#------------------------------------------------------------------------------

import os
import sys
import string
import rfc822
import re
import time
import struct, fcntl
import tempfile
import getopt
import ConfigParser
import askversion

#------------------------------------------------------------------------------

class AskConfig:
	"""
	Manages the configuration related information for ASK.

	Attributes:

	- cfg:  				 ConfigParser object
	- home:					 home directory (from $HOME)
	- rc_*: 				 Reflect values set in the configuration file.
	- RET_PROCMAIL_CONTINUE: Signals procmail to continue delivery
	- RET_PROCMAIL_STOP:	 Signals procmail to stop delivery
	"""

	#------------------------------------------------------------------------------
	def __init__(self, argv):
		"""
		Initializes the AskConfig class. 'argv' is used to parse the command
		line options.
		"""
	
		self.procmail_mode = 0
		self.filter_mode   = 0
		self.loglevel      = 0
		self.logfile       = ""
		self.home          = ""
		self.rcfile		   = ""

		self.__cmdline(argv)

		## If self.home is already set, we passed it through command line

		if (self.home == ""):
			self.home = os.getenv("HOME")

		if not self.home:
			sys.stderr.write("ASK ERROR: Cannot find HOME directory! Aborting...\n")
			sys.exit(1)

		## Acquire python's version number and warn if unsupported.

		try:
			self.python_major_version, \
			self.python_minor_version, \
			self.python_micro_version, \
			self.python_releaselevel,  \
			tmp = sys.version_info
		except:
			## Older versions of python do not define sys.version_info
			self.python_major_version = 0
			self.python_minor_version = 0
			self.python_micro_version = 0
			self.python_releaselevel  = ""

		if not self.rcfile:
			self.rcfile = self.home + "/.askrc"
			
		self.__read_config(self.rcfile)

			
	#------------------------------------------------------------------------------
	def __read_config(self, configfile):
		"""
		Reads config file pointed to by 'configfile' and process the options 
		accordingly. Note that this function will expand lists and environment
		variables found inside the options.
		"""

		if (os.access(configfile, os.R_OK) == 0):
			sys.stderr.write("ERROR: %s does not exist or is unreadable. Exiting...\n" % configfile)
			sys.exit(self.RET_PROCMAIL_CONTINUE)

		self.cfg = ConfigParser.ConfigParser()

		try:
			self.cfg.read(configfile)
		except ConfigParser.MissingSectionHeaderError:
			sys.stderr.write("ERROR: Config file has no headers. Exiting...\n")
			sys.exit(self.RET_PROCMAIL_CONTINUE)
		
		## We now load each of value in turn

		self.rc_mymails     = self.__expand("rc_mymails", listmode = 1)
		self.rc_myfullname  = self.__expand("rc_myfullname", mandatory = 0)
		self.rc_mymailbox   = self.__expand("rc_mymailbox")
		self.rc_junkmailbox = self.__expand("rc_junkmailbox",mandatory = 0)
		self.rc_bulkmailbox = self.__expand("rc_bulkmailbox",mandatory = 0)
		self.rc_mailkey     = self.__expand("rc_mailkey")
		self.rc_md5_key	    = self.__expand("rc_md5_key")
 
 		self.rc_askdir      = self.__expand("rc_askdir")

		## If msgdir ends in "/" we assume messages will be queued in a
		## Maildir compatible format. In that case we add the "cur/" directory
		## to the path, as it will be the "real" directory where the files reside.
		## The delivery routines are smart enough to remove the "cur/new/tmp" part.

		self.rc_msgdir      = self.__expand("rc_msgdir")
		if (self.rc_msgdir[len(self.rc_msgdir) - 1] == "/"):
			
			## Create dirs
			if not os.path.exists(self.rc_msgdir):	os.mkdir(self.rc_msgdir)

			if not os.path.exists(self.rc_msgdir + "cur"): os.mkdir(self.rc_msgdir + "cur")
			if not os.path.exists(self.rc_msgdir + "new"): os.mkdir(self.rc_msgdir + "new")
			if not os.path.exists(self.rc_msgdir + "tmp"): os.mkdir(self.rc_msgdir + "tmp")

			self.rc_msgdir = self.rc_msgdir + "/new/"
			self.queue_is_maildir = 1
		else:
			self.queue_is_maildir = 0

		self.rc_tmpdir      = self.__expand("rc_tmpdir")

		self.rc_lockfile    = self.__expand("rc_lockfile", mandatory = 0)

		self.rc_confirm_mailbody   = self.__expand("rc_confirm_mailbody",   mandatory = 0)

		self.rc_confirm_dirs    = self.__expand("rc_confirm_dirs",   listmode = 1, mandatory = 0)
		self.rc_confirm_langs   = self.__expand("rc_confirm_langs",  listmode = 1, mandatory = 0)

		self.rc_whitelist  = self.__expand("rc_whitelist",  listmode = 1)
		self.rc_ignorelist = self.__expand("rc_ignorelist", listmode = 1)

		# This is kept here for backwards compatibility.
		# The blacklist is now a synonym for ignorelist
		self.rc_blacklist  = self.__expand("rc_blacklist",  listmode = 1, mandatory = 0)

		self.rc_basic_headers = self.__expand("rc_basic_headers", listmode = 1, mandatory = 0)
		self.rc_mta_command   = self.__expand("rc_mta_command")

		self.rc_junk_unknown_recipients = self.__expand("rc_junk_unknown_recipients", mandatory = 0, boolean = 1)

 		self.rc_whitelist_on_mailkey = self.__expand("rc_whitelist_on_mailkey", mandatory = 0, boolean = 0)

 		self.rc_remote_cmd_enabled  = self.__expand("rc_remote_cmd_enabled",     mandatory = 0, boolean = 1)
 		self.rc_remote_cmd_htmlmail = self.__expand("rc_remote_cmd_htmlmail",    mandatory = 0, boolean = 1)

 		self.rc_smtp_validate = self.__expand("rc_smtp_validate", mandatory = 0, boolean = 1)

		## Queued messages older than this will have "Delete" suggested as the default action
 		self.rc_remote_cmd_max_age  = self.__expand_int("rc_remote_cmd_max_age", mandatory = 0, default = 10)

		self.rc_max_attach_lines = self.__expand_int("rc_max_attach_lines", default = 50)

		## Set the max number of confirmations we can have in the list
		## before we stop sending them to that address
		self.rc_max_confirmations = self.__expand_int("rc_max_confirmations", default = 5)

		## Set the Minimum list size for who we have recently sent
		## Confirmation messages to
		self.rc_min_confirmation_list = self.__expand_int("rc_min_confirmation_list", default = 20)

		if self.rc_min_confirmation_list < 2:
			self.rc_min_confirmation_list = 2

		## Set the Maximum list size for who we have recently sent
		## Confirmation messages to
		self.rc_max_confirmation_list = self.__expand_int("rc_max_confirmation_list", default = self.rc_min_confirmation_list * 2)

		if self.rc_max_confirmation_list < self.rc_min_confirmation_list:
			self.rc_max_confirmation_list = self.rc_min_confirmation_list * 2

		## Blacklist will always be treated as ignorelist.
		if self.rc_blacklist:
			self.rc_ignorelist.extend(self.rc_blacklist)

		## We must have either rc_confirm_dirs (in which case we'll use the
		## new rc_confirm_langs) or the old style rc_confirm_mailbody. 

		if (self.rc_confirm_dirs != []):

			## Assume English if no language specified
			if (self.rc_confirm_langs == ""):
				self.rc_confirm_langs = ["en"];

			## Fill in with the filenames

			self.rc_confirm_filenames = []

			for dirname in self.rc_confirm_dirs:
				for lang in self.rc_confirm_langs:
					
					fname = os.path.join(dirname, "confirm_%s.txt" % lang)

					if os.path.isfile(fname):
						self.rc_confirm_filenames.append(fname)
		else:
			if (self.rc_confirm_mailbody != ""):
				self.rc_confirm_filenames = [ self.rc_confirm_mailbody ]
			else:
				sys.stderr.write("ERROR: No confirm_dirs or confirm_body in rcfile. Exiting...\n")
				sys.exit(self.RET_PROCMAIL_CONTINUE)
				
		## Verify if we got something...

		if self.rc_confirm_filenames == []:
			sys.stderr.write("ERROR: No confirmation templates found! Exiting...\n")
			sys.exit(self.RET_PROCMAIL_CONTINUE)

		## Pipe delivery is only supported for Python 2
		if (self.rc_mymailbox[0] == "|" and self.python_major_version < 2):
			sys.stderr.write("ERROR: You need Python 2 to use pipe delivery. Exiting...\n")
			sys.exit(self.RET_PROCMAIL_CONTINUE)

	#------------------------------------------------------------------------------

	def __expand_int(self, option, listmode = 0, mandatory = 1, boolean = 0, default = None):
		"""
		Returns same results as __expand, converted to int.
		Returns 'None' on exception.
		"""
		
		value = self.__expand(option, listmode, mandatory, boolean, default)
		try:
			value = int(value)
		except:
			value = None

		return value
	#------------------------------------------------------------------------------
	def __expand(self, option, listmode = 0, mandatory = 1, boolean = 0, default = None):
		"""
		Returns option 'option' within section 'Ask'. Some mangling will be
		done in the input field:

		- ${VARIABLE} will be expanded.

		If 'listmode' is set, the input will be split into a list (commas will
		be used as the separator).

		If 'mandatory' is set (the default), an error will occur if the variable
		is not found. If mandatory == 0 and the variable does not exist in the
		config file, it will be set to '' (or [] if listmode == 1).

		The 'boolean' argument will cause the interpretation of on/off/true/false/1/0.
		Anything else will cause the parameter to be set to false.

		"""

		try:
			buf = self.cfg.get("ask",option)

		except ConfigParser.NoSectionError, str:
			print "Config file error: %s" % str
			sys.exit(self.RET_PROCMAIL_CONTINUE)

		except ConfigParser.NoOptionError, str:
			if not default == None:
				return default
			if not mandatory:
				if listmode:
					return([])
				else:
					return('')
			print "Config file error: %s" % str
			sys.exit(self.RET_PROCMAIL_CONTINUE)

		except ValueError, str:
			print "Config file error: %s" % str
			sys.exit(self.RET_PROCMAIL_CONTINUE)

		## Remove leading and trailing backspaces
		buf = string.strip(buf)

		## Expand Environment vars

		while 1:
			res = re.search("(\$\{[a-z0-9]*\})", buf, re.IGNORECASE)

			if (res == None):
				break

			env = res.group(1)
			env = env[2:-1]						## Remove ${ and }

			## Expand environment variable, treating $HOME as a special case
			## Non-existent environment variables yield an empty string.

			if env == "HOME":
				result = self.home
			else:
				result = os.getenv(env,"")

			buf = string.replace(buf, res.group(1), result)

		## List?

		if listmode:
			listbuf = string.split(buf, ",")
			return map(lambda str: string.strip(str), listbuf)

		## If boolean, interpret true/false/on/off/1/0

		if boolean:
			if string.lower(buf) in ("true","on","1","yes"):
				return 1
			else:
				return 0

		## Normal case
		return(buf)

	#------------------------------------------------------------------------------
	def	__cmdline(self, cmd):
		"""
		Parses the command line and set the self.rc_* variables accordingly.
		Also sets the return codes for procmail.
		"""
		try:
			(opts, args) = getopt.getopt(cmd[1:], "", ["loglevel=", "logfile=","procmail","filter","home=","rcfile="])
		except getopt.error:
			sys.stderr.write("Use: askfilter [--loglevel=x --logfile=file] [--procmail|--filter] [--home=your_homedir]\n")
			sys.exit(1)

		for o, a in opts:
			if (o == "--loglevel"):
				try:
					self.loglevel = int(a)
				except ValueError:
					sys.stderr.write("Error: --loglevel takes a numeric argument\n")
			if (o == "--logfile"):
				self.logfile = a
			if (o == "--procmail"):
				self.procmail_mode = 1
				self.filter_mode = 0
			if (o == "--filter"):
				self.procmail_mode = 0
				self.filter_mode = 1
			if (o == "--home"):
				self.home = a
			if (o == "--rcfile"):
				self.rcfile = a
		
		## Set procmail return codes accordingly.
		## filter_mode always returns "continue" so procmail or another 
		## generic mail filter process knows when to discard the message

		if self.procmail_mode:
			self.RET_PROCMAIL_CONTINUE = 0
			self.RET_PROCMAIL_STOP     = 1
		else:
			self.RET_PROCMAIL_CONTINUE = 0
			self.RET_PROCMAIL_STOP     = 0

#--------------------------------------------------------------------------------------
