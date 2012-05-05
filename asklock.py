#------------------------------------------------------------------------------
#	asklock.py - File locking functions
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
#	$Id: asklock.py,v 1.7 2006/01/09 04:22:26 paganini Exp $
#------------------------------------------------------------------------------

import os.path
import sys
import fcntl

#------------------------------------------------------------------------------

class AskLock:
	"""
	Opens and closes files, with locking support.
	"""
	
	#------------------------------------------------------------------------------
	# Set of methods to mimic a subset of the most common file object operations
	#------------------------------------------------------------------------------

	def readline(self):
		return self.fh.readline()

	def readlines(self):
		return self.fh.readlines()

	def write(self, str):
		self.fh.write(str)

	def writelines(self, sequence):
		self.fh.writelines(sequence)

	def seek(self, offset, whence = 0):
		self.fh.seek(offset, whence)

	def truncate(self, offset):
		self.fh.truncate(offset)

	#------------------------------------------------------------------------------
	def open(self, filename, mode, lockfile = ""):
		"""
		Open the specified 'filename' using mode 'mode'.
		The optional 'lockfile' can be passed. In that case, the fnctl function
		will be used on that file, instead of 'filename' (useful for NFS
		mounts and other creepy situations).

		Returns the corresponding file object.
		"""

		self.filename = filename
		self.mode     = mode
		self.lockfile = lockfile
		
		self.fh = open(self.filename, self.mode)

		## Use the original filename if the lockfile is empty

		if (self.lockfile == ""):
			self.lockfile = self.filename
			self.fh_lock  = self.fh;
		else:
			if (os.path.isfile(self.lockfile)):
				self.fh_lock = open(self.lockfile, "r+")
			else:
				self.fh_lock = open(self.lockfile, "w")
			
		fcntl.lockf(self.fh_lock.fileno(), fcntl.LOCK_EX)

		## File is locked

		return(self.fh)

	#------------------------------------------------------------------------------
	def close(self):

		## Unlock

		fcntl.lockf(self.fh_lock.fileno(), fcntl.LOCK_UN)

		self.fh.close()
		self.fh_lock.close()
		
		return 0

## EOF ##
