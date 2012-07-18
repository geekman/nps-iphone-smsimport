#
# iPhoneSMSDB.py - iPhone SMS database manipulation
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

from sqlite3 import dbapi2 as sqlite
import phonenumbers
import os

class iPhoneSMSDB:
	"""Class to query and manipulate the iPhone SMS Database."""

	def __init__(self, default_country, sms_db):
		if not os.path.isfile(sms_db):
			raise IOError('database doesn\'t exist: ' + sms_db)

		self.db = sqlite.connect(sms_db)
		self.default_country = default_country.upper()
		self.dirty = False

		# register the user-defined function used by triggers
		# 2nd bit is the "read" bit
		self.db.create_function('read', 1, lambda f: (int(f) & 0x02) >> 1)


	def __del__(self):
		self.close()


	def close(self):
		if self.db:
			self.db.close()
			self.db = None

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

		country = self.get_number_country(address, self.default_country)
		c.execute("INSERT INTO group_member(group_id, address, country) " + 
				"VALUES(?, ?, ?)", 
				(group_id, address, country))
		self.dirty = True

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
		sms['country'] = self.get_number_country(address, self.default_country)

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
		self.dirty = True


	@staticmethod
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

