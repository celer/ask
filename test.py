#!/usr/bin/python

import asklog
import askmail
import askmessage
import askmain

class fakelog:
	def write(self, n, msg):
		print msg

class fakeconfig:
	def __init__(self):
		self.helo_domain = "paganini.net"
		self.envelope_from = "paganini@paganini.net"

log = fakelog()
config = fakeconfig()
mail = askmail.AskMail(config, log)

print mail.smtp_validate("test12345@wiw.org")
