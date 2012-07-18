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

import win32com.client
from   win32com.shell import shell, shellcon
import AMDevice
from iPhoneSMSDB import iPhoneSMSDB

# location of sms.db on the iPhone
IPHONE_SMS_DB = '/var/mobile/Library/SMS/sms.db'

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
		'iphone':			False,
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

	# operate on the device
	dev = None
	afc = None
	if config['iphone']:
		# check for existence of sms.db first
		if os.path.exists(config['smsdb']):
			raise IOError, "iPhone SMS db already exists at '%s' - will not overwrite." % config['smsdb']

		dev = AMDevice.MobileDevice()
		print "waiting for iPhone to be connected...",
		dev.wait()
		if dev.has_device():
			dev.connect()
			print "ok"

			try:
				afc = dev.start_afc("com.apple.afc2")
			except:
				print "You need a jailbroken iPhone to access its filesystem"
				sys.exit(3)

			afc.download_file(IPHONE_SMS_DB, config['smsdb'])

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

	do_commit = False
	if isms.dirty:
		do_commit = True
		if not config['skip_prompt']:
			do_commit = raw_input("commit? (y/N) ").strip().lower() == 'y'

		if do_commit:
			print "committing...",
			isms.commit()
			print "done"
		else:
			print "not commited"
			isms.rollback()
	else:
		print "no changes"

	isms.close()

	# upload back to the iphone, or remove unchanged file
	if config['iphone']:
		if do_commit:
			print "uploading sms.db to iPhone...",
			afc.upload_file(config['smsdb'], IPHONE_SMS_DB)
			print "done"
		else:
			os.unlink(config['smsdb'])

