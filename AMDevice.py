#
# AMDevice.py - Python bindings for iTunesMobileDevice.dll
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

from ctypes import *
import os
import threading
import _winreg

# get InstallDirs for Apple libraries
def _QueryRegValue(key, value_name):
	parts = key.split('\\')
	root_map = {
			'HKLM': _winreg.HKEY_LOCAL_MACHINE,
			'HKCU': _winreg.HKEY_CURRENT_USER,
			}
	path = '\\'.join(parts[1:])
	k = _winreg.OpenKey(root_map[parts[0]], path, 0, _winreg.KEY_READ)

	#v = _winreg.QueryValue(k, value_name)
	# FIXME: workaround for QueryValue()
	v = None
	try:
		i = 0
		while True:
			x = _winreg.EnumValue(k, i)
			if x[0] == value_name:
				v = x[1]
				break
			i += 1
	except WindowsError:
		pass

	_winreg.CloseKey(k)
	return v

APPLE_REG_KEY = 'HKLM\SOFTWARE\Apple Inc.\\'

try:
	os.environ['PATH'] = ';'.join([
			os.environ['PATH'], 
			_QueryRegValue(APPLE_REG_KEY + 'Apple Application Support', 'InstallDir'), 
			_QueryRegValue(APPLE_REG_KEY + 'Apple Mobile Device Support', 'InstallDir'), 
			])
except WindowsError:
	raise RuntimeError, "AppleMobileDeviceSupport and AppleApplicationSupport must be installed"


# Function prototypes are available from reversed C headers at:
# http://theiphonewiki.com/wiki/index.php?title=MobileDevice_Library

# ----- CoreFoundation DLL -----

CoreFoundationDLL		= CDLL('CoreFoundation')

CFStringRef = c_void_p

CFStringMakeConstantString = CoreFoundationDLL.__CFStringMakeConstantString
CFStringMakeConstantString.restype = CFStringRef
CFStringMakeConstantString.argtypes = [c_char_p]

# ----- iTunesMobileDevice DLL -----

iTunesMobileDeviceDLL	= CDLL('iTunesMobileDevice')

am_device_p = c_void_p

# error codes
MDERR_OK                = 0
MDERR_SYSCALL           = 0x01
MDERR_OUT_OF_MEMORY     = 0x03
MDERR_QUERY_FAILED      = 0x04 
MDERR_INVALID_ARGUMENT  = 0x0b
MDERR_DICT_NOT_LOADED   = 0x25

# AFC errors
MDERR_AFC_OUT_OF_MEMORY	= 0x03
MDERR_AFC_NOT_FOUND		= 0x08
MDERR_AFC_ACCESS_DENIED	= 0x09

# for device notification
ADNCI_MSG_CONNECTED     = 1
ADNCI_MSG_DISCONNECTED  = 2
ADNCI_MSG_UNSUBSCRIBED  = 3

class am_device_notification(Structure):
	pass

class am_device_notification_callback_info(Structure):
	_fields_ = [
			('dev',		am_device_p),
			('msg',		c_uint),
			('subscription', POINTER(am_device_notification)),
			]

am_device_notification_callback = CFUNCTYPE(None, 
		POINTER(am_device_notification_callback_info), c_int)

am_device_notification._fields_ = [
		('unknown0',	c_uint),
		('unknown1',	c_uint),
		('unknown2',	c_uint),
		('callback',	am_device_notification_callback),
		('cookie',		c_uint),
		]

am_device_notification_p = POINTER(am_device_notification)

AMDeviceNotificationSubscribe = iTunesMobileDeviceDLL.AMDeviceNotificationSubscribe
AMDeviceNotificationSubscribe.restype = c_uint
AMDeviceNotificationSubscribe.argtypes = [
		am_device_notification_callback, c_uint, c_uint, c_uint, 
		POINTER(POINTER(am_device_notification)) ]

AMDeviceNotificationUnsubscribe = iTunesMobileDeviceDLL.AMDeviceNotificationUnsubscribe
AMDeviceNotificationUnsubscribe.restype = c_uint
AMDeviceNotificationUnsubscribe.argtypes = [ POINTER(am_device_notification) ]

AMDeviceIsPaired = iTunesMobileDeviceDLL.AMDeviceIsPaired
AMDeviceIsPaired.restype = c_uint
AMDeviceIsPaired.argtypes = [ am_device_p ]

AMDeviceConnect = iTunesMobileDeviceDLL.AMDeviceConnect
AMDeviceConnect.restype = c_uint
AMDeviceConnect.argtypes = [ am_device_p ]

AMDeviceRelease = iTunesMobileDeviceDLL.AMDeviceRelease
AMDeviceRelease.restype = None
AMDeviceRelease.argtypes = [ am_device_p ]

AMDeviceValidatePairing = iTunesMobileDeviceDLL.AMDeviceValidatePairing
AMDeviceValidatePairing.restype = c_uint
AMDeviceValidatePairing.argtypes = [ am_device_p ]

AMDeviceStartSession = iTunesMobileDeviceDLL.AMDeviceStartSession
AMDeviceStartSession.restype = c_uint
AMDeviceStartSession.argtypes = [ am_device_p ]

AMDeviceStopSession = iTunesMobileDeviceDLL.AMDeviceStopSession
AMDeviceStopSession.restype = c_uint
AMDeviceStopSession.argtypes = [ am_device_p ]

AMDeviceStartService = iTunesMobileDeviceDLL.AMDeviceStartService
AMDeviceStartService.restype = c_uint
AMDeviceStartService.argtypes = [ am_device_p, CFStringRef, POINTER(c_int) ]

# AFC
afc_connection_p = c_void_p
afc_file_ref = c_uint64

AFCConnectionOpen = iTunesMobileDeviceDLL.AFCConnectionOpen
AFCConnectionOpen.restype = c_uint
AFCConnectionOpen.argtypes = [ c_int, c_uint, POINTER(afc_connection_p) ]

AFCConnectionClose = iTunesMobileDeviceDLL.AFCConnectionClose
AFCConnectionClose.restype = c_uint
AFCConnectionClose.argtypes = [ afc_connection_p ]

AFCRemovePath = iTunesMobileDeviceDLL.AFCRemovePath
AFCRemovePath.restype = c_uint
AFCRemovePath.argtypes = [ afc_connection_p, c_char_p ]

AFCFileRefOpen = iTunesMobileDeviceDLL.AFCFileRefOpen
AFCFileRefOpen.restype = c_uint
AFCFileRefOpen.argtypes = [ afc_connection_p, c_char_p, c_int, c_int, POINTER(afc_file_ref) ]

AFCFileRefClose = iTunesMobileDeviceDLL.AFCFileRefClose
AFCFileRefClose.restype = c_uint
AFCFileRefClose.argtypes = [ afc_connection_p, afc_file_ref ]

AFCFileRefLock = iTunesMobileDeviceDLL.AFCFileRefLock
AFCFileRefLock.restype = c_uint
AFCFileRefLock.argtypes = [ afc_connection_p, afc_file_ref ]

AFCFileRefUnlock = iTunesMobileDeviceDLL.AFCFileRefUnlock
AFCFileRefUnlock.restype = c_uint
AFCFileRefUnlock.argtypes = [ afc_connection_p, afc_file_ref ]

AFCFileRefRead = iTunesMobileDeviceDLL.AFCFileRefRead
AFCFileRefRead.restype = c_uint
AFCFileRefRead.argtypes = [ afc_connection_p, afc_file_ref, c_void_p, POINTER(c_uint) ]

AFCFileRefWrite = iTunesMobileDeviceDLL.AFCFileRefWrite
AFCFileRefWrite.restype = c_uint
AFCFileRefWrite.argtypes = [ afc_connection_p, afc_file_ref, c_void_p, c_uint ]


class AFCFile:
	def __init__(self, afc_svc, path, mode):
		self.afc_svc = afc_svc
		self.path = path
		self.fh = afc_file_ref()

		# determine flags to use
		open_flag = 0
		for m in mode:
			if m == 'w':		open_flag |= os.O_WRONLY + 1
			elif mode == 'r': 	open_flag |= os.O_RDONLY + 1
			else:
				raise ValueError, "invalid file mode '%s'" % mode

		r = AFCFileRefOpen(self.afc_svc.afc_conn, path, open_flag, 0, byref(self.fh))
		if r != MDERR_OK:
			raise IOError, "cannot open file '%s' res=%d" % (path, r)

	def __del__(self):
		self.close()

	def __repr__(self):
		return 'AFCFile("%s")' % self.path

	def close(self):
		if self.fh:
			AFCFileRefClose(self.afc_svc.afc_conn, self.fh)
			self.fh.value = 0

	def lock(self):
		AFCFileRefLock(self.afc_svc.afc_conn, self.fh)

	def unlock(self):
		AFCFileRefUnlock(self.afc_svc.afc_conn, self.fh)

	def read(self, size=4096):
		buf = create_string_buffer(size)
		c_size = c_uint(size)
		r = AFCFileRefRead(self.afc_svc.afc_conn, self.fh, buf, byref(c_size))
		if r != MDERR_OK:
			raise IOError, "read error %d" % r
		elif c_size.value == 0:
			return None
		return buf.raw

	def write(self, data):
		buf = create_string_buffer(data)
		size = sizeof(buf) - 1	# buffer is NUL terminated
		r = AFCFileRefWrite(self.afc_svc.afc_conn, self.fh, buf, size)
		if r != MDERR_OK:
			raise IOError, "write error %d" % r

class AFCService:
	def __init__(self, dev, service_name="com.apple.afc"):
		self.afc_sock = c_int()
		self.afc_conn = afc_connection_p()
		self.service_name = service_name

		if AMDeviceStartService(dev.dev, 
				CFStringMakeConstantString(service_name), 
				byref(self.afc_sock)) != MDERR_OK:
			raise RuntimeError, "unable to start service %s" % service_name

		if AFCConnectionOpen(self.afc_sock, 0, byref(self.afc_conn)) != MDERR_OK:
			raise RuntimeError

	def __del__(self):
		if self.afc_conn:
			AFCConnectionClose(self.afc_conn)

	def __repr__(self):
		return 'AFCService(%s)' % self.service_name

	def remove_path(self, path):
		return AFCRemovePath(self.afc_conn, c_char_p(path))

	def open_file(self, path, mode):
		return AFCFile(self, path, mode)

	def download_file(self, src_path, dst_path):
		"""Downloads src_path from iDevice to local dst_path.
		Local destination will be overwritten without warning."""

		f = self.open_file(src_path, 'r')
		dst_file = open(dst_path, 'wb')
		if not dst_file:
			raise IOError, "unable to open dest file '%s'" % dst_path

		while True:
			data = f.read()
			if not data:
				break
			dst_file.write(data)

		dst_file.close()
		f.close()

	def upload_file(self, src_path, dst_path):
		dst_file = self.open_file(dst_path, 'w')
		f = open(src_path, 'rb')

		#if dst_file.lock() != MDERR_OK:
		#	raise IOError, "unable to lock file %s" % dst_path

		while True:
			data = f.read(4096)
			if not data:
				break
			dst_file.write(data)
		#dst_file.unlock()

		f.close()
		dst_file.close()

class MobileDevice:
	dev = None
	has_dev = threading.Event()
	notification_p = am_device_notification_p()
	cb_func = None

	def __init__(self):
		def cbfunc(info_p, cookie):
			info = info_p.contents
			dev = info.dev
			if info.msg == ADNCI_MSG_UNSUBSCRIBED:
				return

			self.dev = dev
			self.has_dev.set()

		# prevent gc on callback function
		self.cb_func = am_device_notification_callback(cbfunc)
		r = AMDeviceNotificationSubscribe(self.cb_func,
				0, 0, 0, byref(self.notification_p));
		if r != MDERR_OK:
			raise RuntimeError

	def __del__(self):
		AMDeviceStopSession(self.dev)
		AMDeviceRelease(self.dev)
		AMDeviceNotificationUnsubscribe(self.notification_p)

	def wait(self, timeout=None):
		self.has_dev.wait(timeout)

	def has_device(self):
		return self.has_dev.is_set() and self.dev is not None

	def connect(self):
		if AMDeviceConnect(self.dev) != MDERR_OK: raise RuntimeError
		if AMDeviceIsPaired(self.dev) != 1:
			raise RuntimeError, "if your phone is locked with a passcode, unlock then reconnect it"

		if AMDeviceValidatePairing(self.dev) != MDERR_OK: raise RuntimeError
		if AMDeviceStartSession(self.dev) != MDERR_OK: raise RuntimeError

	def start_afc(self, service_name="com.apple.afc"):
		return AFCService(self, service_name)

