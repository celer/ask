#------------------------------------------------------------------------------
#	askmain.py -- Main class for ASK
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
#	$Id: askmain.py,v 1.49 2006/01/09 04:22:26 paganini Exp $
#------------------------------------------------------------------------------

import sys
import askversion
import asklog
import askconfig
import askmail
import askmessage
import askremote

#------------------------------------------------------------------------------
#	MAIN
#------------------------------------------------------------------------------

class AskMain:
	"""
	This is the 'master' class for ask. The typical ASK invocation
	should be something like:

	import asklog
	import askconfig
	import sys

	config = askconfig.AskConfig(sys.argv)
	log    = asklog.AskLog(config.logfile)
	log.loglevel = config.loglevel

	ask = askmain.AskMain()
	rc = ask.filter(sys.stdin)

	sys.exit(rc)


	Attributes:

	- config: CONFIG object
	- log:    LOG object
	- msg:    MESSAGE object
	- rmt: 	  REMOTE_COMMAND object
	"""

	def __init__(self, config, log):
		"""
		This is the constructor for the ASK tool. It will create instances
		of all objects needed for proper operation. The caller is supposed to
		pass valid config and log instances.
		"""

		self.config = config
		self.log    = log
		self.msg    = askmessage.AskMessage(config, log)
		self.rmt    = askremote.AskRemote(self.msg, config, log)

	def filter(self, filehandle):
		"""
		Reads (and process) the contents of the mail message pointed to by
		the file object 'filehandle'. The return code MUST be used by
		the caller to exit the program.
		"""
		
		## Initial Logging
		self.log.write(1, "")
		self.log.write(1, "----- ASK v%s Started -----" % askversion.AskVersion.version)

		## Warn if incompatible version of Python is found
		if (self.config.python_major_version < 2 and
		    self.config.python_minor_version < 2 and 
			self.config.python_minor_version < 2):
			self.log.write(1, "WARNING: Incompatible version of Python detected (%d.%d.%d). Proceed at your own risk!" %
				(self.config.python_major_version, self.config.python_minor_version, self.config.python_minor_version))

		self.msg.read(filehandle)

		## Header Logging

		self.log.write(1, "Message from:    %s <%s>" % self.msg.get_sender())

		for (recipient_name, recipient_mail) in self.msg.get_recipients():
			self.log.write(1, "Message to:      %s <%s>"  % (recipient_name, recipient_mail))

		self.log.write(1, "Message Subject: %s" % self.msg.get_subject())

        ## If the address is in the whitelist, deliver immediately,
        ## unless the message is a confirmation return or any other
        ## "control" message.  Delivering blindly would make it
        ## impossible for people with two pending messages to confirm
        ## more than one as subsequent confirmation returns would be
        ## blindly delivered.

		if  ((not self.msg.is_confirmation_return()) and
			(not self.msg.is_from_mailerdaemon())   and
			(not self.rmt.is_remote_command())      and
			self.msg.is_in_whitelist()):

			self.log.write(1, "Whitelist match [%s]. Delivering..." % self.msg.list_match)
			self.msg.deliver_mail("Whitelist match [%s]" % self.msg.list_match)
			return(self.config.RET_PROCMAIL_CONTINUE)
		else:
			self.log.write(1, "Not matched in the whitelist")

		## People in ignorelist are just thrown into the void...
		if self.msg.is_in_ignorelist():
			self.log.write(1, "Ignorelist Match. Throwing message away...")
			self.msg.discard_mail()
			return(self.config.RET_PROCMAIL_STOP)

		## Ignore messages coming from MAILER-DAEMON (or postmaster) containing the
		## X-AskVersion header (they are most certainly a result of
		## an invalid sender address)

		if self.msg.is_from_mailerdaemon():
			self.log.write(1, "Sender is mailer-daemon")

			if self.msg.sent_by_ask():
				self.log.write(1, "Header X-AskVersion found. Probable invalid reply from a confirmation message. Ignoring.")
				self.msg.discard_mail()
				return(self.config.RET_PROCMAIL_STOP)
			else:
				self.log.write(1, "Header X-AskVersion not found. Copying directly to mailbox.")
				self.msg.deliver_mail("Message from Mailer-Daemon")
				return(self.config.RET_PROCMAIL_CONTINUE)
		else:
			self.log.write(1, "Sender is not mailer-daemon")

		## Auth:
		## - MD5 matches, Time matches:  Definitely sent by US. Deliver to mailbox
		## - MD5 matches, Time does not: May be a fake or too old. Junk.
		## - MD5 does not match: Definitely not ours. Try to process normally

		if (self.msg.validate_auth_md5()):
			if (self.msg.validate_auth_time(7)):
				self.log.write(1, "Message authenticated (sent by ASK). Delivering...")
				self.msg.deliver_mail("Authenticated Message from ASK")
				return(self.config.RET_PROCMAIL_CONTINUE)
			else:
				self.log.write(1, "Message is authentic but seems too old (could be a fake). Delivering to Junk...")
				self.msg.junk_mail("(Junk) Authentication time expired")
				self.msg.discard_mail()
				return(self.config.RET_PROCMAIL_STOP)

		## If remote commands are enabled, we check for a command request

		if self.config.rc_remote_cmd_enabled:
			self.log.write(1, "Checking for remote commands")

			if self.rmt.process_remote_commands():
				## In filter mode, we always tell the filter to discard
				## the message. The results of remote commands are always
				## delivered directly to the mailbox, as procmail cannot
				## deal with more than one email anyways.

				if self.config.filter_mode:
					self.msg.discard_mail()

				return(self.config.RET_PROCMAIL_STOP)

		##	Is the message a confirmation return message?

		if self.msg.is_confirmation_return():

			## If we find a queued message using the confirmation MD5
			## the user is added to the whitelist and the message
			## is appended to my mailbox
			
			if self.msg.confirmation_msg_queued():
				self.msg.add_to_whitelist()
				self.msg.add_queued_msg_to_whitelist()
				self.msg.dequeue_mail("Confirmed by User")
			else:
				self.log.write(1, "Queued message not found for this confirmation number. Delivering...")
				self.msg.deliver_mail("Invalid confirmation")

			return(self.config.RET_PROCMAIL_CONTINUE)
		else:
			self.log.write(5, "Message is not a confirmation return")

		## If the message contains our MAILKEY, we assume it is a
		## response of some kind, so we let it pass (and optionally,
		## add to whitelist too)

		if (self.msg.has_our_key()):
			
			## Add to whitelist if configured to do so (and not already there)

			if self.config.rc_whitelist_on_mailkey:
				self.msg.add_to_whitelist()
				self.log.write(1, "Found mailkey. Adding to whitelist")

			self.log.write(1, "Our key was found in the message. Delivering...")
			self.msg.deliver_mail("Our key was found in the mail")
			return(self.config.RET_PROCMAIL_CONTINUE)

		## At this point, messages with our mailkey should have been processed.
		## If a message comes from US (without the mailkey) either it's a fake
		## From: line or a reply of some kind that does not include the original

		if self.msg.is_from_ourselves():
			self.log.write(1, "Message comes from us but does not contain our key. Delivering to Junk")
			self.msg.junk_mail("(Junk) Message from self without the mailkey")
			self.msg.discard_mail()
			return(self.config.RET_PROCMAIL_STOP)

		## Before we send out the confirmation, we check for mailing lists
		## If it's a mailing list (not treated by our whitelist above), it
		## will be Junked (confirmations to mailing lists is a big no no)

		if self.msg.is_mailing_list_message():
			self.log.write(1, "Message from %s looks like a mailing list message" % self.msg.get_sender()[1])
			self.msg.bulk_mail("(Bulk) Mailing list message (not in whitelist)")
			self.msg.discard_mail()
			return(self.config.RET_PROCMAIL_STOP)

		## Message already queued? If so, don't send confirmation

		if self.msg.is_queued():
			self.log.write(1, "Message is already queued. Won't resend.")
			self.msg.discard_mail()
			return(self.config.RET_PROCMAIL_STOP)

		## Attempt to validate the sender via SMTP, if configured to do so.
		## If the sender is deemed invalid, discard this message.

		if self.config.rc_smtp_validate:
			if self.msg.valid_smtp_sender():
				self.log.write(1, "  SMTP validation could not determine that sender is invalid.")
			else:
				self.log.write(1, "  SMTP validation returned invalid sender. Discarding...")
				self.msg.discard_mail()
				return(self.config.RET_PROCMAIL_STOP)

		# Junk the email if it's not in the list of known recipients
		# (and configured to do so in the .askrc file)

		if self.config.rc_junk_unknown_recipients and not self.msg.match_recipient():
			self.msg.junk_mail("(Junk) Message with none of our addresses in recipient list")
			self.msg.discard_mail()
			return(self.config.RET_PROCMAIL_STOP)
			
		## All clear, queue, send confirmation and discard.

		self.log.write(1, "Sending confirmation.")
		self.msg.queue_mail()
		self.msg.send_confirmation()

		self.msg.discard_mail()
		return(self.config.RET_PROCMAIL_STOP)


## EOF ##
