#------------------------------------------------------------------------------
#	askmail.py - mail and mailbox related classes
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
#	$Id: askmail.py,v 1.45 2006/01/09 04:22:26 paganini Exp $
#------------------------------------------------------------------------------

import os
import os.path
import re
import sys
import string
import rfc822
import time
import tempfile
import askversion
import asklog
import askconfig
import asklock
import random

#------------------------------------------------------------------------------

class AskMail:
	"""
	This contains the mailbox delivery routines to be used by ASK.

	Attributes:
	
	- mailfrom: Sender
	- log:      ASKLOG object
	- config:   ASKCONFIG object

	Usage:

	config        = AskConfig.AskConfig(argv)
	log           = AskLog.AskLog("your_log_file")

	mail          = AskMail.AskMail(config, log)
	mail.mailfrom = "youremail@yourdomain.com"

	"""

	#------------------------------------------------------------------------------

	def __init__(self, config, log):
		"""
		Initializes the AskMail class
		"""

		self.config = config
		self.log    = log

		self.simple_headers = 0

		## Defaults

		self.mailfrom = None
		self.fullname = None

	#------------------------------------------------------------------------------

	def	__generate_mailbody(self,
		mailto,
		subject,
		body_filenames,
		attached_msgs = [],
		custom_headers = [],
		custom_footers = [],
		max_attach_lines=-1,
		x_ask_info = None,
		html_mail = 0,
		copyright = 1,
		create_envelope = 0):
		
		"""
		Generates a RFC-822 compliant mail file ready to be delivered
		or piped into sendmail.
		
		mailto
			Email address to be used in the "To:" line

		subject
			Subject of the message

		body_filenames
			List of filenames containing the text to form the body of the email.

		attached_msgs
			List of filenames containing the text to be shown after the 
			'original message follow' line.

		custom_headers
			List of RFC-822 headers to be included in the message

		custom_footers
			Llist of custom footers to be included in the message

		max_attach_lines
			Maximum number of lines to read from the 'attached_msgs'

		html_mail
			If set, causes the generation of HTML mail

		copyright
			If set, causes a copyright footer to be added to each message

		create_envelope
			If set, the initial "From_" line will be create. This parameter
			*must* be set for local (non-sendmail) deliveries.

		INSTANCE VARIABLES:

		self.mailfrom, self.fullname
			Email address to be used in the "From:" line

		self.basic_headers
			If set, only the "From:," "To:," "Subject:," "Cc:," and "Bcc:"
			headers will be preserved from the original attached message.

		RETURNS:

		The filename containing the RFC-822 compliant message.
		"""

		self.log.write(10, "  __generate_mailbody: mailfrom=%s, mailto=%s, subject=%s" %
			(self.mailfrom, mailto, subject))

		temp = "%s.%d" % (tempfile.mktemp(), os.getpid())
		self.log.write(10, "  __generate_mailbody: tempfile=" + temp)

		fh = open(temp, "w")

		## Create 'From_' line
		if create_envelope:
			fh.write("From %s %s\n" % (self.mailfrom, time.asctime()))

		## Create 'From:' line
		if self.fullname:
			fromline = 'From: "%s" <%s>' % (self.fullname, self.mailfrom)
		else:
			fromline = 'From: %s' % self.mailfrom
			
		## Create 'Date:' line

		#if daylight:
		#	tzoffset = "%02.2d%02.2d" %
		#		((time.timezone - time.altzone) / 3600,
		#		 ((time.timezone - time.altzone) % 3600) / 60)
		#else:
		#	tzoffset = "%02.2d%02.2d" %
		#		((time.timezone) / 3600,
		#		 ((time.timezone) % 3600) / 60)

		dateline = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime())	

		fh.write(fromline    + "\n")
		fh.write("To: "      + mailto   + "\n")
		fh.write("Subject: " + subject  + "\n")
		fh.write("Date: "    + dateline + "\n")
		fh.write("X-AskVersion: " + askversion.AskVersion.version + " (http://www.paganini.net/ask)\n")

		## Process HTML Mail

		if html_mail:
			fh.write("Content-Type: text/html; charset=\"iso-8859-1\"\n")
			fh.write("Mime-Version: 1.0\n")

		## X-ASK-Info
		if x_ask_info:
			fh.write("X-ASK-Info: %s (%s)\n" % (x_ask_info, time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(time.time()))))

		## Write the custom headers
		for var in custom_headers:
			fh.write(var + "\n")

		fh.write("\n")			## Header / Message separator

		## Write non RFC-822 bodies

		for var in body_filenames:
			self.log.write(10, "  __generate_mailbody: body_filename=%s" % var)

			fbody = open(var, "r")

			while 1:
				buf = fbody.readline();
				if buf == '':
					break

				## Quote "From:" Lines
				if (buf[0:5] == 'From '):
					buf = ">" + buf

				fh.write(buf)

			fh.write("\n")		## Separator
			fbody.close()

		## Shameless copyrights

		if copyright:
			if html_mail:
				fh.write("<p><font size=\"-1\">\n")
				fh.write("This email account is protected by:<br>\n")
				fh.write("<a href=\"%s\">Active Spam Killer</a> (ASK) V%s - (C) 2001-2004 by Marco Paganini<br>\n"
					% (askversion.AskVersion.url, askversion.AskVersion.version))
				fh.write("For more information visit <a href=\"%s\">%s</a>\n"
					% (askversion.AskVersion.url, askversion.AskVersion.url))
				fh.write("</font><p>")
			else:
				fh.write("This email account is protected by:\n")
				fh.write("Active Spam Killer (ASK) V%s - (C) 2001-2004 by Marco Paganini\n" % askversion.AskVersion.version)
				fh.write("For more information visit %s\n\n" % askversion.AskVersion.url)

		## Only write separator *IF* there's something to be added at the end

		if len(attached_msgs):
			if html_mail:
				fh.write("<b>Original Message Follows:</b>\n<hr>\n")
			else:
				fh.write("--- Original Message Follows ---\n\n")

		## Write RFC-822 bodies, mangling headers if necessary

		for var in attached_msgs:
			self.log.write(10, "  __generate_mailbody(): attached_msgs=%s" % var)

			fbody = open(var, "r")

			in_headers = 1

			## We only send max_attach_lines (if not -1)
			max_lines = max_attach_lines

			if html_mail:
				print "<pre>\n"

			while (max_lines >= 0 or max_attach_lines == -1):

				buf = fbody.readline()
				if (buf == ''):
					break

				## End of headers?
				if len(string.strip(buf)) == 0:
					in_headers = 0

				## Mangle, if necessary
				if (self.config.rc_basic_headers != [] and in_headers):
					hdr = string.split(buf)[0]				## First word
					if hdr not in self.config.rc_basic_headers:
						continue;
				
				## Quote "From:" Lines in any_case
				if (buf[0:5] == 'From '):
					buf = ">" + buf

				fh.write(buf)

				## Headers do not count in the maximum number of lines in attachment
				
				if not in_headers:
					max_lines = max_lines - 1

			## Indicate the original was truncated if needed

			if (max_attach_lines != -1 and max_lines <= 0):
				fh.write("\n(Original message truncated)\n")

			if html_mail:
				print "</pre><p>\n"
			else:
				fh.write("\n")

		## Write custom footers
		for var in custom_footers:
			fh.write(var + "\n")

		fh.write("\n")		## Separator
		fh.close()

		return(temp)

	#------------------------------------------------------------------------------

	def	deliver_mail_file(self, mailbox, mailfile, x_ask_info=None, uniq = None,
								custom_headers = []):
		"""
		Delivers mail contained in 'mailfile' (no checks are done to make sure
		it's in RFC-822 format) into 'mailbox'. This method appends the contents
		of 'mailfile' to 'mailbox', doing fcntl style locking first. We assume
		a maildir style mailbox if the mailbox name ends with a "/".
		'x_ask_info' will generate an "X-ASK-Info" header on the email. Custom
		RFC-822 headers can be specified with by passing the desired headers in
		the 'custom_headers' list.  If "mailbox" is "-", stdout will be used.
		The 'uniq' parameter can be used to override the value of the 'uniq' field
		(the second field in a Maildir mailfile). If not set, the current
		uid will be used.
		"""

		self.log.write(1, "  deliver_mail_file: Delivering mail from %s to mailbox %s" % (mailfile, mailbox))

		## Get the 'headers' from custom_headers
		def get_header(x):	return(string.lower(string.split(x)[0]))
		custom_headers_only = map(get_header, custom_headers)

		if not os.path.isfile(mailfile):
			self.log.write(1, "  deliver_mail_file: ERROR: Cannot open %s" % mailfile)
			return -1

		## If mailbox == "-", we use stdout. If it ends with a slash, it's
		## a Maildir mailbox. If it starts with a "|" we consider it a pipe.
		## Otherwise we assume mbox format

		using_maildir = 0
		using_stdout  = 0
		using_pipe    = 0

		## Stdout
		if (mailbox == "-"):
			using_stdout = 1
			mailbox = "stdout"		## Just for printing purposes
			self.log.write(5, "  deliver_mail_file: delivering to stdout")
			fh_mbox = sys.stdout

		## Maildir Format
		elif (mailbox[len(mailbox) - 1] == "/"):
			using_maildir = 1
			
			## Remove '/cur' '/new' and '/tmp' (jumps back to the root of the mailbox)
			mailbox = string.replace(mailbox, "/cur", "")
			mailbox = string.replace(mailbox, "/new", "")
			mailbox = string.replace(mailbox, "/tmp", "")

			if not uniq:
				uniq = os.getuid()

			## Try until the mailfile is not there. If it's there,
			## wait for a random amount of time and try again

			while 1:
				filetime         = int(time.time())
				maildir_file     = os.path.join(mailbox, "tmp", "%ld.%s.%s" % (filetime, uniq, (os.uname())[1]))
				maildir_file_new = string.replace(maildir_file, "tmp/", "new/")

				if not (os.path.exists(maildir_file) or os.path.exists(maildir_file_new)):
					fh_mbox = open(maildir_file, "w")
					break
				else:
					self.log.write(10, "  deliver_mail_file: Maildir file exists. Sleeping and retrying...")
					time.sleep(int(random.random() * 3) + 1)

			self.log.write(5, "  deliver_mail_file: Mailbox format: Maildir, tmp filename=%s" % maildir_file)

		## Pipe to program (No locking!)

		elif (mailbox[0] == "|"):
			using_pipe = 1
			mailbox = mailbox[1:]	## Remove pipe symbol
			self.log.write(5, "  deliver_mail_file: delivering to a pipe (%s)" % mailbox)
			fh_mbox = os.popen(mailbox, "w")

		## Mbox format
		else:
			self.log.write(5, "  deliver_mail_file: Mbox format")

			lockf = ""
			if self.config.rc_lockfile != "":
				lockf = self.config.rc_lockfile + "." + os.path.basename(mailbox)

			fh_mbox = asklock.AskLock()
			fh_mbox.open(mailbox, "a", lockf)
		
		## We suppose the file is unlocked when we get here...

		fh_mailfile = open(mailfile, "r")
		
		in_headers = 1;
		lastbuf = '';

		while 1:
			buf = fh_mailfile.readline();

			if (buf == ''):
				break

			## When the headers are exhausted (single crlf), we write the
			## X-ASK-Info header and our custom headers.

			if (len(string.strip(buf)) == 0 and in_headers):
				in_headers = 0

				## X-ASK-Info
				if x_ask_info:
					fh_mbox.write("X-ASK-Info: %s (%s)\n" % (x_ask_info, time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(time.time()))))
				
				## Write the custom headers
				for var in custom_headers:
					fh_mbox.write(var + "\n")

			## Header processing

			if in_headers:
				mail_header = string.lower(string.split(buf)[0])

				## Always remove the "Delivered-To" header when doing pipe
				## deliveries. This header is added to the message on the
				## "final" delivery (usually when email was received) and
				## will cause a false "mail-loop" when trying to re-send
				## this message using postfix if the recipient's address
				## shows here.

				if (using_pipe and mail_header == "delivered-to:"):
					continue

				## Custom_headers will replace existing headers
				if mail_header in custom_headers_only:
					continue

			fh_mbox.write(buf)
			lastbuf = buf

		fh_mailfile.close()
		
		## If lastbuf is not an empty line, we add one. mbox style messages
		## must always end in a newline

		if (len(string.strip(lastbuf)) != 0 and (not using_maildir)):
			fh_mbox.write("\n")

		## Unlock and close
		if not using_stdout:
			fh_mbox.close()

		## Rename mailbox from 'tmp' to 'new' directory
		if using_maildir:
			self.log.write(5, "  deliver_mail_file: Renaming maildir file %s to %s\n" % (maildir_file, maildir_file_new))
			os.rename(maildir_file, maildir_file_new)

		self.log.write(1, "  deliver_mail_file: Message delivered to %s" % mailbox)

		return 0

	#------------------------------------------------------------------------------

	def deliver_mail(self,
		mailbox,
		mailto,
		subject,
		body_filenames,
		attached_msgs = [],
		custom_headers = [],
		custom_footers = [],
		max_attach_lines=-1,
		uniq = None,
		x_ask_info = None,
		html_mail = 0,
		copyright = 0):

		"""
		Delivers mail to the specified mailbox. The email is formed from the
		parameters passed to the method. See __generate_body for the parameter
		description.
		"""

		self.log.write(10, "  deliver_mail: mailbox = %s, mailfrom=%s, mailto=%s, subject=%s" %
			(mailbox, self.mailfrom, mailto, subject))

		temp = self.__generate_mailbody(mailto           = mailto,
								   		subject          = subject,
								   		body_filenames   = body_filenames,
								   		attached_msgs    = attached_msgs,
								   		custom_headers   = custom_headers,
								   		custom_footers   = custom_footers,
								   		max_attach_lines = max_attach_lines,
								   		x_ask_info		 = x_ask_info,
								   		html_mail        = html_mail,
								   		copyright        = copyright,
								   		create_envelope  = 1)

		## Physically deliver mail
		self.deliver_mail_file(mailbox, temp, x_ask_info = None, uniq = uniq)
		os.unlink(temp)

	#------------------------------------------------------------------------------

	def	send_mail(self,
		mailto,
		subject,
		body_filenames,
		attached_msgs = [],
		custom_headers = [],
		custom_footers = [],
		max_attach_lines=-1,
		x_ask_info = None,
		html_mail = 0,
		copyright = 1):

		"""
		Sends an email from the user set in self.fromuser to 'mailto'. Check
		the method __generate_body for more details.
		"""

		self.log.write(1, "  send_mail: mailfrom=%s, mailto=%s, subject=%s" %
			(self.mailfrom, mailto, subject))

		temp = self.__generate_mailbody(mailto           = mailto,
								   		subject          = subject,
								   		body_filenames   = body_filenames,
								   		attached_msgs    = attached_msgs,
								   		custom_headers   = custom_headers,
								   		custom_footers   = custom_footers,
								   		max_attach_lines = max_attach_lines,
								   		x_ask_info       = x_ask_info,
								   		html_mail        = html_mail,
								   		copyright        = copyright)

		## Call sendmail to send it
		command = string.replace(self.config.rc_mta_command, "MAILFILE", temp)

		ret = os.system(command)
		self.log.write(10, "  send_mail: os.system(%s) returned %d" % (command, ret))
		os.unlink(temp)

	#------------------------------------------------------------------------------

	def	send_mail_file(self, mailto, mailfilename, custom_headers = [], x_ask_info = None):
		"""
		This function will invoke sendmail on the specified 'mailfilename'.
		It will also add the 'custom_headers' to the list of headers in
		the message.
		"""

		## Get the 'headers' from custom_headers
		def get_header(x):	return(string.lower(string.split(x)[0]))
		custom_headers_only = map(get_header, custom_headers)

		self.log.write(10, "  send_mail_file(): mailto=%s, mailfilename=%s" %
			(mailto, mailfilename))

		if not os.path.isfile(mailfilename):
			self.log.write(1, "  send_mail_file: ERROR: Cannot open %s" % mailfilename)
			return -1

		temp = "%s.%d" % (tempfile.mktemp(), os.getpid())
		self.log.write(10, "  send_mail(): tempfile=" + temp)

		fread  = open(mailfilename, "r")
		fwrite = open(temp, "w")

		## Copy 'mailfilename' RFC822 headers to 'temp', eliminating
		## any old X-ASK-Auth headers it finds and adding a new one.

		while 1:
			buf = fread.readline()
			if (buf == ''):
				break

			## End of headers? Write custom headers and proceed to body
			if not buf.rstrip():

				## X-ASK-Info
				if x_ask_info:
					fwrite.write("X-ASK-Info: %s (%s)\n" % (x_ask_info, time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(time.time()))))

				## Custom Headers
				for var in custom_headers:
					fwrite.write(var + "\n")

				fwrite.write("\n")			## Header / Message separator
				break
			else:
				mail_header = buf.lower().split()[0]

				## Always remove the "Delivered-To" header when doing pipe
				## deliveries. This header is added to the message on the
				## "final" delivery (usually when email was received) and
				## will cause a false "mail-loop" when trying to re-send
				## this message using postfix if the recipient's address
				## shows here.

				if mail_header == "delivered-to:":
					continue

				## Custom_headers will replace existing headers
				if mail_header in custom_headers_only:
					continue

			## Copy everything else (except old X-ASK-Auth's)
			if not re.search("^X-ASK-Auth:", buf, re.IGNORECASE):
				fwrite.write(buf)

		## Write body

		while 1:
			buf = fread.readline()
			if (buf == ''):
				break

			fwrite.write(buf)

		fwrite.write("\n")		## Just to be sure there will be a separator...
		fread.close()
		fwrite.close()

		## QUIRK: To avoid adding another line just for a different syntax
		## of sendmail, we resort to using the first argument in rc_mta_command
		## (hopefully the executable name) directly.

		command = string.split(self.config.rc_mta_command)[0] + " " + mailto + " <" + temp

		ret = os.system(command)
		self.log.write(10, "send_mail_file(): os.system(%s) returned %d" % (command, ret))
		os.unlink(temp)

	#------------------------------------------------------------------------------

	def	smtp_validate(self, email, helo_domain = None, envelope_from = None):
		"""
		This method validates a given email address by connecting to the MX servers
		and attempting an initial handshake with the SMTP server. First, we request
		an email to an invalid name. If the server returns 2xx, we understand that
		this server says OK for all cases and return valid. Then, we try our real
		email. If the server returns 5xx, we return "invalid". Any error condition
		results in a "valid" response (meaning that we cannot validate the address
		using an MX query).
		"""

		## Import DNS class. If not found, try ADNS class.

		dnsclass  = 0
		adnsclass = 0

		try:
 			import DNS
			adnsclass = 0
			dnsclass  = 1
		except:
 			self.log.write(1, "  smtp_validate: Cannot import DNS class. Trying ADNS...")

		if not dnsclass:
			try:
				import adns
				adnsclass = 1
				dnsclass  = 0
			except:
				self.log.write(1, "  smtp_validate: Cannot import ADNS class. Feature disabled.")
				return -1

		import smtplib

		## Parse down the email in email and domain

		res = re.match("(.+)@(.+)", email)

		if res:
			username = res.group(1)
			domain   = res.group(2)
		else:
			self.log.write(1, "  smtp_validate: Cannot parse email")
			return -1

		self.log.write(5, "  smtp_validate: user=%s, domain=%s" % (username, domain))

		## Default HELO and ENVELOPE from are the username/domain

		if not helo_domain:
			helo_domain = domain

		if not envelope_from:
			envelope_from = email

		## Retrieve list of MX records and attempt one by one, sorted by priority

		if dnsclass:
			self.log.write(10, "  smtp_validate: Using DNS class")
			dnsobj = DNS.Request(DNS.ParseResolvConf())
			answer = DNS.mxlookup(domain)
			del(dnsobj)
		else:
			self.log.write(10, "  smtp_validate: Using ADNS class")
			s = adns.init()
			(status, cname, expires, answer) = s.synchronous(domain,adns.rr.MXraw)
			del(s)

		mxlist = []
		for (mxpri, mxhost) in answer:
			mxlist.append((mxpri, mxhost))
		mxlist.sort()
		
		for (mxpri, mxhost) in mxlist:
			self.log.write(5, "  smtp_validate: Attempting MX server %s, priority %s" % (mxhost, mxpri))

			## Initial Connection
			try:
				server = smtplib.SMTP(mxhost)
				server.set_debuglevel(0)
			except:
				self.log.write(5, "  smtp_validate: Could not connect to %s" % domain)
				continue

			## Establish the SMTP connection the usual way, then try an "RCPT TO"
			## to an invalid user name. If it says 2xx, we assume this MX says 2xx
			## for everyone and return "valid".

			invalidmail = "askprobe%d@%s" % (int(time.time()), domain)

			cmds = [ 
				("HELO %s"         % helo_domain,		200, 299, -1),
				("MAIL FROM: <%s>" % envelope_from, 	200, 299, -1),
				("RCPT TO: <%s>"   % invalidmail,       500, 599, 1),
				("RCPT TO: <%s>"   % email,             200, 299, 0),
				#("QUIT",                               999, 999, 0)	## Invalid if it got here
			]

			for (cmd, minret, maxret, retcode) in cmds:
					
				self.log.write(10, "  smtp_validate: Sending %s" % cmd)

				try:
					ret = server.docmd(cmd)
				except smtplib.SMTPServerDisconnected:
					self.log.write(5, "  smtp_validate: SMTP server disconnected.")
					break
					
				if ret[0] < minret or ret[0] > maxret:

					self.log.write(1, "  smtp_validate: Command=%s, SMTP code=%d, return=%d" % (cmd, ret[0], retcode))

					if retcode != -1:
						try:
							server.docmd("QUIT")
						except smtplib.SMTPServerDisconnected:
							pass

						del(server)
						return (retcode)
					else:
						break
				else:
					self.log.write(1, "  smtp_validate: Returned SMTP code=%d" % ret[0])

		## Getting here means we couldn't get a satisfactory
		## answer from any of the MX servers

		return -1

## EOF ##
