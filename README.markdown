nps-iphone-smsimport
=====================
**nps-iphone-smsimport** allows you to import SMSes from Samsung phones, 
via the Samsung New PC Studio (NPS) software, into the iPhone SMS database.

The iPhone SMS database can be accessed directly if you are using a 
jailbroken iPhone, using iPhone Explorer or SSH/SFTP directly.
Alternatively, you can also work on the SMS database that was backed 
up by iTunes, then subsequently restore to the iPhone.

**You should backup your data before using this program.**


Typical Usage
--------------
1. Obtain iPhone SMS database, either from an iTunes backup or 
   transferred from a jailbroken phone

2. Sync your Samsung phone with the New PC Studio software

3. Run the `nps-iphone-smsimport.py` script

The script will then find all SMSes in the NPS database. If `--after-date` is 
specified, only SMSes after the specified date will be processed.

Duplicate SMSes will not be inserted. SMSes with the same date/time, same 
text content and direction (sent or received) and same phone number will be 
considered duplicates.

EMSes are not supported in the Samsung New PC Studio and therefore have no 
text content. However, for completeness, the script will import these messages 
but with a standard placeholder text. If you do not wish to include EMSes, use 
the `--skip-ems` option to not import them.


Requirements
-------------
You need at least Python 2.6 running Windows on the same machine as the 
Samsung NPS software, or you could copy the database and manually specify
its path.

- Samsung NPS database
- Python 2.6 on Windows
- Python for Windows extensions (pywin32)   
  <http://sourceforge.net/projects/pywin32/>
- Jailbroken iPhone -or- iTunes backup of the iPhone


TODO
-----
- Figure out the `hash` column in the `msg_group` table


License
--------
It should be noted that the bundled *phonenumbers Python library* is **NOT** 
covered under this license. For that, please refer to 
<https://github.com/daviddrysdale/python-phonenumbers>

Copyright (C) 2011 Darell Tan

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

