#
# nps-iphone-smsimport.py - Samsung NPS to iPhone SMS database importer
# Copyright (C) 2011 Darell Tan
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#

import os, sys
import operator
import getopt

from sqlite3 import dbapi2 as sqlite
import win32com.client
from   win32com.shell import shell, shellcon
import phonenumbers


class iPhoneSMSDB:
	"""Class to query and manipulate the iPhone SMS Database."""

	db = None
	default_country = None

	def __init__(self, default_country, sms_db):
		if not os.path.isfile(sms_db):
			raise IOError('database doesn\'t exist: ' + sms_db)

		self.db = sqlite.connect(sms_db)
		self.default_country = default_country.upper()

		# register the user-defined function used by triggers
		# 2nd bit is the "read" bit
		self.db.create_function('read', 1, lambda f: (int(f) & 0x02) >> 1)


	def __del__(self):
		if self.db:
			self.db.close()


	def commit(self):
		"""Commits the database"""
		self.db.commit()


	def rollback(self):
		"""Rolls back changes to the database"""
		self.db.rollback()


	def _form_address_query(self, address):
		numbers = [address,]
		try:
			pnumber = phonenumbers.parse(address, self.default_country)
			numbers.append(phonenumbers.format_number(pnumber, 
								phonenumbers.PhoneNumberFormat.NATIONAL))
			numbers.append(phonenumbers.format_number(pnumber, 
								phonenumbers.PhoneNumberFormat.INTERNATIONAL))
		except:
			pass

		# strip spaces
		numbers = set([x.replace(' ', '') for x in numbers])

		# prepare as SQL IN() fragment
		return "replace(address,' ','') IN (%s)" % \
					(','.join(["'%s'" % (x) for x in numbers]))


	def _dict_to_sql_insert(self, sql_stm, d):
		"""Converts a dict and SQL statement prefix, returns an INSERT 
		prepared statement and values."""

		return '%s(%s) VALUES(%s)' % (
					sql_stm, 
					','.join(d.keys()), 
					','.join(['?'] * len(d))), \
				d.values()


	def get_latest_sms_date(self):
		c = self.db.cursor()
		c.execute("SELECT MAX(date) FROM message;")
		latest_sms_ts = c.fetchone()[0]
		return latest_sms_ts


	def get_group_id(self, address):
		"""Retrieves the group_id given an "address"."""

		c = self.db.cursor()
		c.execute("SELECT group_id FROM group_member " + 
				"WHERE " + self._form_address_query(address))
		res = c.fetchone()
		return res and res[0] or None


	def add_group(self, address):
		"""Adds a group for the given "address" and returns the group_id."""

		c = self.db.cursor()
		c.execute("INSERT INTO msg_group(type, unread_count, hash) " + 
				"VALUES(0, 0, NULL)")
		group_id = c.lastrowid

		country = get_number_country(address, self.default_country)
		c.execute("INSERT INTO group_member(group_id, address, country) " + 
				"VALUES(?, ?, ?)", 
				(group_id, address, country))

		return group_id


	def sms_exists(self, sms):
		"""Tests if the specified SMS (dict) already exists.
		Matches SMS contents (text), date and "address"."""

		c = self.db.cursor()
		c.execute('SELECT * FROM message ' + 
					'WHERE text = ? AND date = ? AND (flags & 1) = ? AND ' +
					self._form_address_query(sms['address']), 
						(sms['text'], sms['date'], sms['flags'] & 1))
		return c.fetchone() is not None


	def insert_sms(self, sms):
		"""Inserts the given SMS.
		Checks if the address of the SMS already has a group, otherwise calls 
		add_group() to add one before inserting the SMS."""

		address = sms['address']
		group_id = self.get_group_id(address)
		if group_id is None:
			group_id = self.add_group(address)

		# fill in the country of the number
		sms['country'] = get_number_country(address, self.default_country)

		# update group_id in sms
		sms['group_id'] = group_id

		# add additional columns
		opts = {
				'replace':			0,
				'association_id':	0,
				'height':			0,
				'UIFlags':			4,
				'version':			0,
				}

		sms = dict(sms.items() + opts.items())

		stm, vals = self._dict_to_sql_insert('INSERT INTO message', sms)

		c = self.db.cursor()
		c.execute(stm, vals)


def get_number_country(number, default_country):
	"""Retrieves the country code for a given number. If no international 
	prefix was found, uses the specified "default_country"."""

	country = default_country
	try:
		p = phonenumbers.parse(number, default_country.upper())
		country = phonenumbers.region_code_for_number(p)
	except phonenumbers.NumberParseException:
		pass
	return country.lower()


def read_NPS_sms(nps_db_path=None, filters=[]):
	"""Reads SMSes from the Samsung New PC Studio (NPS) internal database."""

	# locate NPS database
	if not nps_db_path:
		appdata_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0)
		nps_db_path = os.path.join(appdata_dir, 'Samsung', 'New PC Studio', 'Guest.dat')

	if not os.path.isfile(nps_db_path):
		raise IOError('unable to find Samsung NPS database at ' + nps_db_path)

	adoconn = win32com.client.Dispatch(r'ADODB.Connection')
	DSN = 'PROVIDER=Microsoft.Jet.OLEDB.4.0;DATA SOURCE=' + nps_db_path
	adoconn.Open(DSN)
	rs = win32com.client.Dispatch(r'ADODB.Recordset')

	rs.Cursorlocation = 3;
	nps_sql = "SELECT *, IIF(SENDER IS NOT NULL, 2, 3) AS FLAGS FROM MESSAGE"
	if filters:
		nps_sql += " WHERE " + " AND ".join(filters)
	rs.Open(nps_sql, adoconn);

	sms = []
	if (rs.RecordCount):
		while not rs.EOF:
			address = None
			if rs.Fields.Item('Sender').Value:
				address = rs.Fields.Item('Sender').Value
			else:
				address = rs.Fields.Item('Receiver').Value

			# skip SMSes with no address - these are likely drafts
			if address is None:
				rs.MoveNext()
				continue

			# strip trailing semicolon
			address = address.replace(';', '')

			s = {
				'address':	address,
				'text':		rs.Fields.Item('Content').Value,
				'date':		int( rs.Fields.Item('Create_date').Value ),
				'flags':	rs.Fields.Item('Flags').Value,
				}

			if rs.Fields.Item('Type').Value == 'EMS':
				s['text'] = '<Imported EMS Placeholder>';

			sms.append(s)

			rs.MoveNext()

	return sms

def print_usage():
	print """
NPS SMS Importer.

%s --country <country> [--smsdb <x> | --npsdb <x> | --verbose ] ...

args:

  --country <country>
      Specifies the country code, for mobile numbers without 
      international prefix. Usually the country where your SMSes originate.

  --after-date <mm/dd/yyyy>
      Only import SMSes after the specified date. The date format must be 
	  understood by MS Access, or just use the "mm/dd/yyyy" format.

  --smsdb <iphone-sms.db>
      Specifies iPhone SMS database file
	  By default, "sms.db" in the current directory is used

  --npsdb <nps-db.dat>
      Specifies the Samsung NPS database file (usually called "Guest.dat")
      By default, this is at "%%AppData%%\Samsung\New PC Studio\Guest.dat"

  --dry-run
      Performs all the steps, but discards changes to the iPhone SMS database
	  at the end. Specifying this flag will skip the final "commit?" prompt.

  --skip-ems
      Skips EMSes, which include SMSes longer than 160 characters.

  --skip-prompt
      Supresses the prompt to commit the imported SMSes

  --verbose
      Prints raw SMS details (can be specified multiple times)
""" % (sys.argv[0])
	

if __name__ == '__main__':
	config = {
		'npsdb':			None,
		'smsdb':			'sms.db',
		'verbose':			0,
		'skip_prompt':		False,
		'country':			None,
		'after_date':		'',
		'dry_run':			False,
		'skip_ems':			False,
	}

	try:
		def needs_arg(k):
			return config[k] is None or type(config[k]) is str

		opts, args = getopt.getopt(sys.argv[1:], '', 
				[k.replace('_', '-') + ("=" if needs_arg(k) else "") 
					for k in config.keys()])
	except getopt.GetoptError, err:
		print 'error: ', str(err)
		print_usage()
		sys.exit(2)

	for opt, arg in opts:
		opt = opt[2:].replace('-', '_')

		if type(config[opt]) is bool:
			config[opt] = True
		elif type(config[opt]) is int:
			config[opt] = config[opt] + 1
		else:
			# needs arg
			config[opt] = arg

	if not config['country']:
		print "error: country was not specified"
		print_usage()
		sys.exit(2)

	# process NPS filters
	nps_filters = []
	nps_filters.append("(TYPE = 'SMS'" + 
			("" if config['skip_ems'] else " OR TYPE = 'EMS'") + 
			")")
	if config['after_date']:
		nps_filters.append("CREATE_DATE >= #%s#" % (config['after_date']))

	nps_sms = read_NPS_sms(config['npsdb'], nps_filters)
	isms = iPhoneSMSDB(config['country'], config['smsdb'])

	count_total		= 0
	count_empty		= 0
	count_dup		= 0
	count_inserted	= 0
	count_newgrp	= 0

	for s in sorted(nps_sms, key=operator.itemgetter('date')):
		count_total += 1

		if not s['text'] or not s['text'].strip():
			count_empty += 1
			if config['verbose'] >= 2: print "skipping empty SMS", s
			continue

		if isms.sms_exists(s):
			if config['verbose'] >= 2: print "duplicate SMS", s
			count_dup += 1
		else:
			if not isms.get_group_id(s['address']):
				if config['verbose']: print "adding group for", s['address']
				count_newgrp += 1
			if config['verbose']: print "inserting SMS", s
			isms.insert_sms(s)
			count_inserted += 1

	print
	print "new groups:\t", count_newgrp
	print
	print "empty:\t\t", count_empty
	print "duplicate:\t", count_dup
	print "inserted:\t", count_inserted
	print "TOTAL:\t\t", count_total
	print

	if config['dry_run']:
		isms.rollback()
		sys.exit(0)

	do_commit = True
	if not config['skip_prompt']:
		do_commit = raw_input("commit? (y/N) ").strip().lower() == 'y'

	if do_commit:
		print "committing...",
		isms.commit()
		print "done"
	else:
		print "not commited"

