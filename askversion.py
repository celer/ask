#!/usr/bin/python
#------------------------------------------------------------------------------
#	askversion.py
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
#	$Id: askversion.py,v 1.14 2006/01/09 04:22:27 paganini Exp $
#------------------------------------------------------------------------------

class AskVersion:
	"""
	This class is a simple placeholder for the current version number and
	other "global" information.
	"""

	version = "2.5.3"
	url     = "http://www.paganini.net/ask"

## Main

if __name__ == "__main__":
	print "Active Spam Killer (ASK), version " + AskVersion.version
	print "For more information, please visit " + AskVersion.url

## EOF
