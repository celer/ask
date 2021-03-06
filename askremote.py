#------------------------------------------------------------------------------
#	askremote.py
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
#	$Id: askremote.py,v 1.59 2006/01/09 04:22:27 paganini Exp $
#------------------------------------------------------------------------------

import os
import os.path
import re
import string
import tempfile
import time
from hashlib import md5
import re
import asklog
import askconfig
import askmessage
import askmail
import HTMLParser

#------------------------------------------------------------------------------

class AskRemote:
	"""
	This class deals with remote execution messages.
	
	Attributes:

	- askmsg:	AskMessage Object
	- config:  	CONFIG object
	- log:     	LOG object
	"""

	#----------------------------------------------------------------------------------
	def __init__(self, askmsg, config, log):
		"""
		Initializes the class instance (Duh!)
		"""

		## Initialize the LOG, CONFIG and MAIL objects

		self.config        = config
		self.askmsg        = askmsg
		self.log           = log

		self.user_command  = ''				## The command as sent by the user
		self.user_args     = ''				## The command arguments

		self.edit_help = """
You've requested to edit one of your ASK lists. To complete the
request:

1) Hit the Reply button.

2) The original contents of your list file are shown between the delimiters
   below. Edit the contents at will but do not remove the "start" and "end"
   delimiters.

3) Send the mail back.

ASK knows how to handle most "quoting" chars (the ">" signs your mailer
inserts before each line). They'll be removed automatically.

ASK will refuse to save the list if your original list was modified in the
meantime (for instance, if someone replied to a confirmation message and
was added to the list). In that case, another message will be sent back
indicating this fact and you'll be presented the opportunity to re-edit the
list.

Some list syntax examples:

#Match all users at sourceforge.net
from .*@sourceforge.net

#Match all users at all hosts in the fsf.org domain
from .*@.*fsf.org
"""

		self.edit_failed = """
EDIT FAILED!

Your original ASK list (white/ignore) was modified on your server
after you made the original edit request. This is normally caused by a user
responding to a confirmation (which causes his email to be added to the
list). Please edit your list text below and re-submit the request.

"""
	#------------------------------------------------------------------------------
	def set_user_command(self, str):
		"""
		Saves the passed string (usually the user command as found in the
		"Subject:" field) to the "user_command" attribute.
		"""
		
		self.user_command = str

	#------------------------------------------------------------------------------
	def get_user_command(self, str):
		"""
		Returns the command saved in the "user_command" attribute.
		"""
		
		return(self.user_command)

	#------------------------------------------------------------------------------
	def set_user_args(self, str):
		"""
		Saves the passed string (usually the user command argument as found in the
		"Subject:" field) to the "user_args" attribute.
		"""
		
		self.user_args = str

	#------------------------------------------------------------------------------
	def get_user_args(self):
		"""
		Returns the command saved in the "user_args" attribute.
		"""
		
		return(self.user_args)

	#------------------------------------------------------------------------------
	def is_remote_command(self):
		"""
		Returns true if the current message is a remote command request. False
		otherwise.
		"""
		
		self.log.write(1, "  is_remote_command(): Verifying the subject...")
		return self.process_remote_commands(check_only = 1)

	#------------------------------------------------------------------------------
	def	process_remote_commands(self, check_only = 0):
		"""
		Verify if the current message contains remote commands. If so, process
		accordingly. Returns true if delivery happened, false otherwise.

		A special case happens when the 'check_only' parameter is set. In this
		case, the method will return 1 if the current email contains remote
		commands or 0 otherwise.
		"""

		## If the message does not come from us, ignore it
		if not self.askmsg.is_from_ourselves():
			self.log.write(10, "  process_remote_commands(): Message is not from ourselves")
			return 0

		## IMPORTANT NOTE:
		##
		## cmds *MUST* be defined locally as it references objects defined within its
		## own instance. Defining cmds as self.cmds in the constructor will create a cyclic
		## reference that prevents the deletion of this object.

		cmds = [
			("ask process q", 		  						self.process_queue),
			("ask queue report",    						self.process_textmode_commands),
			("ask edit whitelist[#:]([a-f0-9]{32})$",		self.edit_whitelist),
			("ask edit ignorelist[#:]([a-f0-9]{32})$", 		self.edit_ignorelist),
			("ask edit blacklist[#:]([a-f-0-9]{32})$", 		self.edit_ignorelist), ## Compat ##
			("ask edit whitelist",							self.edit_whitelist),
			("ask edit ignorelist", 						self.edit_ignorelist),
			("ask edit blacklist",  						self.edit_ignorelist), ## Compat ##
			("ask help",  									self.send_help),
			("ask command forward[#:]([a-f0-9]{32})$", 		self.command_forward_mail),
			("ask command delete[#:]([a-f0-9]{32})$", 		self.command_delete_mail),
			("ask command whitelist[#:]([a-f0-9]{32})$", 	self.command_whitelist),
			("ask command ignorelist[#:]([a-f0-9]{32})$",	self.command_ignorelist),
			("ask command blacklist[#:]([a-f0-9]{32})$", 	self.command_ignorelist), ## Compat ##
		]

		subject = self.askmsg.get_subject()
		self.log.write(10, "  process_remote_commands(): Subject=" + subject)

		ret = 0		## Default == No delivery

		for (subject_re, method) in cmds:
			res = re.search(subject_re, subject, re.IGNORECASE)

			if res:
				self.log.write(1, "  process_remote_commands(): Found subject=\"%s\"" % subject)

				if check_only:
					self.log.write(1, "  process_remote_commands(): Checking only. Returning true")
					ret = 1
					break

				## Save the command and the argument requested by the user
				self.set_user_command(subject)

				if string.find(subject_re, "(") != -1:
					self.set_user_args(res.group(1))
					self.log.write(10, "  process_remote_commands(): User args = %s" % res.group(1))
				else:
					self.set_user_args(None)
					self.log.write(10, "  process_remote_commands(): User args = None")


				method() 	## Execute method
				ret = 1		## All methods cause some type of delivery
				break

		del cmds
		return ret
	
	#------------------------------------------------------------------------------
	def	command_forward_mail(self):
		"""
		Delivers the queued email to the user's mailbox, unless we're operating
		in 'procmail' or 'filter' mode *and* using text mode for the remote commands.
		In that case, the file will be re-sent to the user's primary address using sendmail
		instead. This is necessary to make allow procmail/filter users to dequeue multiple
		messages at once. The email has the X-ASK-Auth header added, so it will
		pass directly thru the next invocation of ASK and be correctly processed
		by the mail filter.
		"""

		## Set the effective MD5 to the one passed on the Subject
		self.askmsg.set_conf_md5(self.get_user_args())

		if ((self.config.procmail_mode or self.config.filter_mode) and
		    (not self.config.rc_remote_cmd_htmlmail)):
			self.log.write(10, "  command_forward_mail: Text mode AND procmail/filter. Will forward to self")
			via_smtp = 1
		else:
			self.log.write(10, "  command_forward_mail: Delivering directly")
			via_smtp = 0

		self.askmsg.dequeue_mail("Forwarded by Command",
								 mailbox = self.config.rc_mymailbox,
								 via_smtp = via_smtp)

	#------------------------------------------------------------------------------
	def command_delete_mail(self):
		"""
		Deletes the email pointed to by the user_args.
		"""

		## Set the effective MD5 to the one passed on the Subject
		self.askmsg.set_conf_md5(self.get_user_args())

		self.askmsg.delete_mail

	#------------------------------------------------------------------------------
	def	process_textmode_commands(self):
		"""
		This function will go through the mail text and process everything that
		looks like a remote command in textmode.
		"""
		
		self.askmsg.fh.seek(0)

		while 1:

			buf = self.askmsg.fh.readline()

			if (buf == ''):
				break

			## Look for anything like N... Id: MD5
			res = re.search("([nibwrd]).*Id: ([a-f0-9]{32})", buf, re.IGNORECASE)

			if not res:
				continue

			action = res.group(1)
			md5    = res.group(2)

			self.log.write(1, "  process_textmode_commands(): Action [%s], MD5 [%s]" % (action, md5))

			## We set the user_args to the md5 we need. Note that the
			## idea was to 'encapsulate' this in such a way that we
			## don't have to mess with 'md5' inside the askmessage
			## object, but for now, it's still confusing so we'll
			## set on both.

			## MD5 used by this module's methods
			self.set_user_args(md5)
			
			## MD5 used by the askmessage class
			self.askmsg.set_conf_md5(md5)
			
			if self.askmsg.confirmation_msg_queued():
				if action == 'I':	## Add sender to IgnoreList
					self.command_ignorelist()
				elif action == 'B':	## Old "Blacklist" command now adds to ignorelist
					self.command_ignorelist()
				elif action == 'W':	## Add sender to Whitelist
					self.command_whitelist()
				elif action == 'R':	## Remove mail from queue
					self.askmsg.delete_mail()
				elif action == 'D':	## Deliver but don't whitelist
					self.command_forward_mail()
			else:
				self.log.write(1, "  process_textmode_commands(): Queued message was not found. Ignoring...")

	#------------------------------------------------------------------------------
	def process_queue(self, htmlmode = -1):
		"""
		Will go through the queue and send the user a list of options
		available for each message.  If the 'textmode' parameter is set,
		the email will be sent in text format (as opposed to HTML).
		"""

		## If no htmlmode is specified, use the settings found
		## in self.config.rc_remote_cmd_htmlmail

		if htmlmode == -1:
			htmlmode = self.config.rc_remote_cmd_htmlmail

		aMail          = askmail.AskMail(self.config, self.log)
		aMail.fullname = self.config.rc_myfullname
		aMail.mailfrom = self.config.rc_mymails[0]

		tempFile       = "%s.%d" % (tempfile.mktemp(), os.getpid())
		tempFileHandle = open(tempFile, "w")
		
		queueDir       = self.config.rc_msgdir
		queueFiles     = os.listdir(queueDir)

		## Reverse sort list of files by mtime
		
		def mtime_file(x,queue=queueDir):  return(os.stat(queue + "/" + x)[8], x)	## Convert to (mtime,filename)
		def strip_mtime(x):	return(x[1])											## Strip mtime

		queueFiles = map(mtime_file, queueFiles)	## Convert to (mtime,filename)[]
		queueFiles.sort()							## sort (on mtime)
		queueFiles.reverse()						## Descending
		queueFiles = map(strip_mtime, queueFiles)	## Strip mtime
		
		##

		if htmlmode:
			tempFileHandle.write("<html>\n")
			tempFileHandle.write("<body>\n")

		if len(queueFiles) > 0:

			if not htmlmode:
				tempFileHandle.write("""
ASK QUEUE REPORT

These are the contents of your ASK queue. These emails are sitting in the
queue waiting for a confirmation from the sender. Change the "N" on the left
of each email with the desired action. Actions are:

N - Do Nothing. Leave it queued.
D - Deliver this message to my In-Box.
W - Deliver this message to my In-Box and add sender to Whitelist.
R - Delete this message from the Queue.
I - Delete this message from the Queue and ignore future emails.

Just edit the message as you wish and reply. Quotes are OK.
Queue contents:

""")
			#---

			for oneMessageFile in queueFiles:

				aFileHandle = open(queueDir + "/" + oneMessageFile, "r")
				aMessage    = askmessage.AskMessage(self.config, self.log)
				aMessage.read(aFileHandle)
				aFileHandle.close()
				
				## Printable Date & Time

				msg_date = ""
				try:
					msg_date = time.ctime()
				except:
					pass

				if not msg_date:
					msg_date = "[Invalid]"

				## Get last "Received: from" header that contains an IP and 
				## is not from localhost (127.x.x.x)

				received_from = ''

				headerlist = aMessage.msg.getallmatchingheaders("Received")
				headerlist.reverse()

				for header in headerlist:
					header = string.strip(header)

					if (re.search(" from.*[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*", header) and
						(not re.search(" from.*127\.[0-9]*\.[0-9]*\.[0-9]*", header))):
						received_from = header[9:]	## Strip "Received:"
						break

				## Get all X-ASK-Info headers.

				askinfolist = []

				for header in aMessage.msg.getallmatchingheaders("X-ASK-Info"):
					header = string.strip(header)
					askinfolist.append(header[12:])	## Strip "X-ASK-Info:"

				## File Size

				filesize     = os.path.getsize(queueDir + "/" + oneMessageFile)
				filesize_str = "%d bytes" % filesize

				if filesize > 1024:
					filesize = filesize / 1024
					filesize_str = "%s KB" % filesize
					
				if filesize > 1048576:
					filesize = filesize / 1024
					filesize_str = "%s MB" % filesize


				## Grab the MD5 from the filename (user may have changed key, etc, etc)
				res = re.search("([a-f0-9]{32})", oneMessageFile, re.IGNORECASE)

				if not res:
					self.log.write(1, "  process_queue(): Could not find MD5 for file %s. Ignored" % oneMessageFile)
					continue
				
				file_md5 = res.group(1)

				self.log.write(10, "  process_queue(): filename=%s, file_md5=%s" % (oneMessageFile, file_md5))

				if htmlmode:
					tempFileHandle.write('<hr><br>\n')
					tempFileHandle.write('<table border=0 width="100%">\n')

					tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>From:</b></td>\n')
					tempFileHandle.write('<td>%s</td>\n' % aMessage.strip_html(aMessage.get_sender()[1]))
					tempFileHandle.write('<td></td>\n')
					tempFileHandle.write('<tr>\n')

					tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>Subject:</b></td>\n')
					tempFileHandle.write('<td>%s</td>\n' % aMessage.strip_html(aMessage.get_subject()))
					tempFileHandle.write('<td></td>\n')
					tempFileHandle.write('<tr>\n')

					tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>Date:</b></td>\n')
					tempFileHandle.write('<td>%s</td>\n' % msg_date)
					tempFileHandle.write('<td></td>\n')
					tempFileHandle.write('<tr>\n')

					tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>Received:</b></td>\n')
					tempFileHandle.write('<td>%s</td>\n' % received_from)
					tempFileHandle.write('<td></td>\n')
					tempFileHandle.write('<tr>\n')

					first = 1
					for x_ask_info in askinfolist:
						if first:
							tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>X-ASK-Info:</b></td>\n')
							first = 0
						else:
							tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><br></td>\n')

						tempFileHandle.write('<td>%s</td>\n' % x_ask_info)
						tempFileHandle.write('<td></td>\n')
						tempFileHandle.write('<tr>\n')

					tempFileHandle.write('<td width="5%" bgcolor="#B0B0FF"><b>Size:</b></td>\n')
					tempFileHandle.write('<td>%s</td>\n' % filesize_str)
					tempFileHandle.write('<td></td>\n')
					tempFileHandle.write('<tr>\n')

					## Read Preview

					summary = aMessage.summary(300)

					tempFileHandle.write('<td colspan=3 bgcolor="#F0F0F0">\n')
					tempFileHandle.write('<font size=-1><b>Message Preview</b><p>\n')

					tempFileHandle.write(summary)

					tempFileHandle.write('</td>\n')
					tempFileHandle.write('</tr>\n')

					tempFileHandle.write('<td align="left" colspan=3>\n')
					tempFileHandle.write('<table border=0 width="100%">\n')
					tempFileHandle.write('<td align="center" bgcolor="#E0E0E0"><font size="-1"><a href="mailto:%s?subject=ask command forward:%s">Deliver to my Inbox</font></td>\n' % (self.config.rc_mymails[0], file_md5))
					tempFileHandle.write('<td align="center" bgcolor="#E0E0E0"><font size="-1"><a href="mailto:%s?subject=ask command whitelist:%s">Deliver to my Inbox<br>and Add Sender to Whitelist</font></td>\n' % (self.config.rc_mymails[0], file_md5))
					tempFileHandle.write('<td align="center" bgcolor="#E0E0E0"><font size="-1"><a href="mailto:%s?subject=ask command delete:%s">Delete Message<br>From the Queue</font></td>\n' % (self.config.rc_mymails[0], file_md5))
					tempFileHandle.write('<td align="center" bgcolor="#E0E0E0"><font size="-1"><a href="mailto:%s?subject=ask command ignorelist:%s">Delete Message from the Queue<br>and Ignore Future e-mails</font></td>\n' % (self.config.rc_mymails[0], file_md5))
					tempFileHandle.write('</table>')

					tempFileHandle.write('</td>\n')
					tempFileHandle.write('</tr>\n')
					
					tempFileHandle.write('</table>\n')
					tempFileHandle.write('<br><br>\n')

					del aMessage

				else:

					## Default action == D (delete) if the file is older than
					## rc_remote_cmd_max_age days.

					filetime = os.path.getmtime(os.path.join(queueDir, oneMessageFile))
					now      = time.time()

					if (filetime < (now - (self.config.rc_remote_cmd_max_age * 86400))):
						default_action = "R"
					else:
						default_action = "N"
					
					tempFileHandle.write("%s  Id: %s\n" % (default_action, file_md5))
					tempFileHandle.write("   From:       %s\n" % aMessage.get_sender()[1])
					tempFileHandle.write("   Subject:    %-65.65s\n" % aMessage.get_subject())
					tempFileHandle.write("   Date:       %s,    Size: %s\n" % (msg_date, filesize_str))

					## X-ASK-Info

					for x_ask_info in askinfolist:
						tempFileHandle.write("   X-ASK-Info: %-65.65s\n" % x_ask_info)

					## Read summary
					summary = aMessage.summary(300)

					tempFileHandle.write("\n")
					tempFileHandle.write("%s\n" % summary)

					tempFileHandle.write("\n------------------------------------------------------------\n\n")

		else:
			tempFileHandle.write("The message queue is empty\n")

		#---

		if htmlmode:
			tempFileHandle.write("</body>\n")
			tempFileHandle.write("</html>\n")

		tempFileHandle.close()

		aMail.deliver_mail(mailbox        = self.config.rc_mymailbox,
						   mailto         = self.config.rc_mymails[0],
						   subject        = "ASK queue report",
						   body_filenames = [tempFile],
						   custom_headers = [ "X-ASK-Auth: %s" % self.askmsg.generate_auth(), "Precedence: bulk" ],
						   html_mail      = htmlmode)
		os.unlink(tempFile)

	#------------------------------------------------------------------------------
	def send_help(self):
		"""
		Sends the help file the the sender.		
		"""
		
		boundary_text = "=_ASKMessageSegment-AOK_="
		mail_to       = self.config.rc_mymails[0]

		help_text = """
ASK HELP Message

ASK recognizes the following "special" subjects:

ask help
	Returns this message

ask process queue
	Sends you a list of mail in your queue and lets you act on them
 
ask edit whitelist
	Allows you to edit your whitelist

ask edit ignorelist
	Allows you to edit your ignorelist

For more information about ASK (Active Spam Killer), please visit:
http://www.paganini.net/ask
"""
		################   END PLAINTEXT - START HTML #############

		help_html = """
<html>
  <head>
  <title>ASK HELP</title>
  <meta http-equiv="content-type" content="text/html\; charset=ISO-8859-1">
</head>
<body>
<br>
ASK understands several commands. All these commands are
issued by sending mail to yourself with special subjects. These subjects are:
<p>
<dl>
  <dt><a href="mailto:%s?subject=ask%%20help">ask help</a></dt>
  <dd><p>Returns this message</dd>
  <br>

  <dt><a href="mailto:%s?subject=ask%%20process%%20queue">ask process queue</a></dt>
  <dd><p>Sends you a list of mail in your queue and lets you act on them</dd>
  <br>

  <dt><a href="mailto:%s?subject=ask%%20edit%%20whitelist">ask edit whitelist</a></dt>
  <dd><p>Allows you to edit your whitelist</dd>
  <br>

  <dt><a href="mailto:%s?subject=ask%%20edit%%20ignorelist">ask edit ignorelist</a></dt>
  <dd><p>Allows you to edit your ignorelist</dd>
</dl>
<p>
For more information about ASK (Active Spam Killer), please visit
<a href="http://www.paganini.net/ask">ASK's Homepage</a>
<p>
</body>
</html>
""" % (mail_to, mail_to, mail_to, mail_to)

		full_message = help_text + "\n--" + boundary_text + "\nContent-Type: text/plain; charset=\"iso-8859-1\"\n\n" + help_text + "\n--" + boundary_text + "\nContent-Type: text/html; charset=\"iso-8859-1\"\n\n" + help_html + "\n--" + boundary_text + "--\n\n"
		tempFile = "%s.%d" % (tempfile.mktemp(), os.getpid())
		tempFileHandle = open(tempFile, "w")
		tempFileHandle.write(full_message)
		tempFileHandle.close()

		aMail = askmail.AskMail(self.config, self.log)

		aMail.fullname = self.config.rc_myfullname
		aMail.mailfrom = mail_to

		aMail.deliver_mail(mailbox        = self.config.rc_mymailbox,
						   mailto         = mail_to,
						   subject        = "ASK Help",
						   body_filenames = [tempFile],
						   custom_headers = ["Content-Type: multipart/alternative;\n\tboundary=\"" + boundary_text + "\"",
											 "MIME-Version: 1.0",
											 "X-ASK-Auth: %s" % self.askmsg.generate_auth(),
											 "Precedence: bulk" ])
		os.unlink(tempFile)

	#------------------------------------------------------------------------------
	def command_ignorelist(self):
		"""
		Adds the message pointed at by the md5 value to the
		ignorelist and then deletes the message.
		"""

		## Set the effective MD5 to the one passed on the Subject
		self.askmsg.set_conf_md5(self.get_user_args())

		queueFileName   = self.askmsg.queue_file(self.askmsg.conf_md5)

		## Create a new AskMessage instance with the queued file
		aMessage        = askmessage.AskMessage(self.config, self.log)
		queueFilehandle = open(queueFileName, "r")

		aMessage.read(queueFilehandle)
		queueFilehandle.close()

		self.log.write(1, "  command_ignorelist(): Adding message %s to ignorelist" % queueFileName)
		aMessage.add_to_ignorelist()

		self.askmsg.delete_mail()

	#------------------------------------------------------------------------------
	def command_whitelist(self):
		"""
		Adds the message pointed at by the md5 stored in
		user_args to the whitelist, and delivers the message.
		"""

		## Set the effective MD5 to the one passed on the Subject
		self.askmsg.set_conf_md5(self.get_user_args())

		## Create a new AskMessage instance with the queued file,
		## so we can get add the sender's email to the whitelist.

		queued_fname = self.askmsg.queue_file(self.askmsg.conf_md5)
		askmsg       = askmessage.AskMessage(self.config, self.log)
		queued_fh    = open(queued_fname, "r")

		askmsg.read(queued_fh)
		queued_fh.close()

		self.log.write(1, "  command_whitelist(): Adding message %s to whitelist" % queued_fname)
		askmsg.add_to_whitelist()

		## Dequeue and remove the queued file
		self.command_forward_mail()

	#------------------------------------------------------------------------------
	def edit_whitelist(self):
		"""
		Sends the whitelist file to the sender.		
		"""

		whitelistFileName = self.config.rc_whitelist[0]
		self.__edit_file(whitelistFileName, "Whitelist")

	#------------------------------------------------------------------------------
	def edit_ignorelist(self):
		"""
		Sends the ignorelist file to the sender.		
		"""
		ignorelistFileName = self.config.rc_ignorelist[0]
		self.__edit_file(ignorelistFileName, "Ignorelist")

	#------------------------------------------------------------------------------
	def __edit_file(self, file_path, file_description):
		"""
		Do the actual work of checking if the file exists, matching
		the md5 value from self.askmsg, and then calling
		__save_file and __send_file as appropriate
		"""

		message_subject = "ASK Edit " + file_description

		## User args will contain the file MD5 if this is a request to
		## Save the file or None if it's a request to Send the file to self

		if os.path.exists(file_path):
			if self.get_user_args():
				if self.fileMatchesMD5(file_path, self.get_user_args()):
					self.__save_file(file_path)
					self.__send_file(file_path, message_subject, "FILE SAVED!\n\n" + self.edit_help)
				else:
					self.__send_file(file_path, message_subject, self.edit_failed + "\n" + self.edit_help)
			else:
				self.log.write(1, "  edit_file(): Sending whitelist to self...")
				self.__send_file(file_path, message_subject, self.edit_help)
		else:
			self.log.write(1, "  edit_file(): Sending whitelist to self...")
			self.__send_file(file_path, message_subject, self.edit_help)

	#------------------------------------------------------------------------------
	def fileMatchesMD5(self, fileName, asciiMD5):
		"""
		Check to see if the file at the given path matches the md5
		checksum
		"""

		if (os.access(fileName, os.F_OK) != 1):
			return 0

		fileHandle = open(fileName, "r")

		## Create a new MD5 object
		md5sum = hashlib.md5()

		while 1:
			buf = fileHandle.readline()

			if (buf == ''):
				break

			md5sum.update(buf)

		fileHandle.close()
	
		ascii_digest = ''
		binary_digest = md5sum.digest()

		for ch in range(0,len(binary_digest)):
			ascii_digest = ascii_digest + "%02.2x" % ord(binary_digest[ch])

		return ascii_digest == asciiMD5
		
	#------------------------------------------------------------------------------
	def __save_file(self, fileName):
		"""
		Saves part of the current message between delimiters to the passed
		filename. "Quoting" chars are removed in the process.
		"""

		self.log.write(1, "  Saving file %s" % fileName)

		fileHandle = open(fileName + ".new", "w")
		
		buf = ''
		self.askmsg.fh.seek(0)

		## Read all the way until "-- start file" tag is found

		while 1:
			buf = self.askmsg.fh.readline()

			if (buf == ''):
				fileHandle.close()
				return 0

			buf = string.strip(buf)
			buf = self.__dequote(buf)

			if string.find(buf, "--- start file") == 0:
				break

		## Read contents until "--- end file" tag is found

		while 1:
			buf = self.askmsg.fh.readline()

			if (buf == ''):
				fileHandle.close()
				return 0

			buf = string.strip(buf)
			buf = self.__dequote(buf)

			if string.find(buf, "--- end file") == 0:
				break

			fileHandle.write("%s\n" % buf)

			
		fileHandle.close()

		# Let's be atomic
		os.rename(fileName + ".new", fileName)

	#------------------------------------------------------------------------------
	def __send_file(self, filename, subject, bonus_text = ""):
		"""
		Sends the given filename with the given subject.
		This file will be in the appropriate format to be edited and
		resubmitted for update
		"""
		
		localTempFile       = "%s.%d" % (tempfile.mktemp(), os.getpid())
		localTempFileHandle = open(localTempFile, "w")

		localTempFileHandle.write("%s\n" % bonus_text)
		localTempFileHandle.write("\n")
		localTempFileHandle.write("--- start file %s ---\n" % filename)

		## Better create a file if it isn't there yet
		if not os.path.exists(filename):
			sendFileHandle = open(filename, "w")
			sendFileHandle.close()

		sendFileHandle = open(filename, "r")

		## Create a new MD5 object
		md5sum = hashlib.md5()

		while 1:
			buf = sendFileHandle.readline()

			if (buf == ''):
				break

			localTempFileHandle.write(buf)
			md5sum.update(buf)
	
		ascii_digest = ''
		binary_digest = md5sum.digest()

		for ch in range(0,len(binary_digest)):
			ascii_digest = ascii_digest + "%02.2x" % ord(binary_digest[ch])


		localTempFileHandle.write("--- end file %s ---\n" % filename)
		localTempFileHandle.close()
		sendFileHandle.close()

		aMail          = askmail.AskMail(self.config, self.log)
		aMail.fullname = self.config.rc_myfullname
		aMail.mailfrom = self.config.rc_mymails[0]

		aMail.deliver_mail(mailbox 		  = self.config.rc_mymailbox,
						   mailto  		  = self.config.rc_mymails[0],
						   subject 		  = "%s#%s" % (subject, ascii_digest),
						   body_filenames = [localTempFile],
						   custom_headers = [ "X-ASK-Auth: %s" % self.askmsg.generate_auth(), "Precedence: bulk" ])

		os.unlink(localTempFile)

	#------------------------------------------------------------------------------
	def __dequote(self, str):
		"""
		This method will remove most quoting chars inserted by mail agents and
		return the unquoted part.
		"""

		res = re.match("^([ \t]*[|>:}][ \t]*)+(.*)", str)

		if res:
			return res.group(2)
		else:
			return str

