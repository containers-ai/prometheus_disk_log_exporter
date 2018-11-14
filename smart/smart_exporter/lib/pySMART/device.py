#Copyright (C) 2014 Marc Herndon
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License,
#version 2, as published by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
This module contains the definition of the `Device` class, used to represent a
physical storage device connected to the system.
Once initialized, class members contain all relevant information about the
device, including its model, serial number, firmware version, and all SMART
attribute data.

Methods are provided for initiating self tests and querying their results.
"""
# Python built-ins
from __future__ import absolute_import
from __future__ import print_function
import re  # Don't delete this 'un-used' import
from subprocess import Popen, PIPE
import warnings

# pySMART module imports
from .attribute import Attribute
from .test_entry import Test_Entry
from .utils import *

class Device(object):
    """
    Represents any device attached to an internal storage interface, such as a
    hard drive or DVD-ROM, and detected by smartmontools. Includes eSATA
    (considered SATA) but excludes other external devices (USB, Firewire).
    """
    def __init__(self, name, interface=None, raid_card=None, raid_params=[]):
        """Instantiates and initializes the `pySMART.device.Device`."""
        assert interface is None or interface.lower() in [
            'ata', 'csmi', 'sas', 'sat', 'sata', 'scsi']
        if '/dev/' in name:
            tmp_list = name.split('/dev/', 1)
            self.prefix = tmp_list[0]
            self.name = tmp_list[-1]
        else:
            self.prefix = ""
            self.name = name
        """
        **(str):** Device's hardware ID, without the '/dev/' prefix.
        (ie: sda (Linux), pd0 (Windows))
        """
        if self.name[:2].lower() == 'pd':
            self.name = pd_to_sd(self.name[2:])

        # Check raid card
        self._raid_type = None
        self._check_raid(raid_card, raid_params)

        self.vendor = None
        """**(str):** Device's vendor name."""
        self.model = None
        """**(str):** Device's model number."""
        self.serial = None
        """**(str):** Device's serial number."""
        self.transport_protocol = None
        """**(str):** Device's transport protocol."""
        self.smart_health_status = None
        """**(str):** Device's smart health status."""
        self.sata_version = None
        """**(str):** Device's SATA version."""
        self.sector_size = None
        """**(str):** Device's sector size."""
        self.percent_used_indicator = None
        """**(str):** Device's percentage used endurance indicator."""
        self.current_drive_temp = None
        """**(str):** Device's current temperature."""
        self.drive_trip_temp = None
        """**(str):** Device's trip temperature."""
        self.spec_cycle_count_over_lifetime = None
        """**(str):** Device's specified cycle count over lifetime."""
        self.accumulated_start_stop_cycles = None
        """**(str):** Device's accumulated start stop cycles."""
        self.element_in_grown_defect_list = None
        """**(str):** Device's element in grown defect list."""
        self.blocks_sent_to_initiator = None
        """**(str):** Device's blocks sent to initiator"""
        self.blocks_received_from_initiator = None
        """**(str):** Device's blocks received from initiator."""
        self.power_up_hours = None
        """**(str):** Device's power up hours."""
        
        self.interface = interface
        """
        **(str):** Device's interface type. Must be one of:
            * **ATA** - Advanced Technology Attachment
            * **SATA** - Serial ATA
            * **SCSI** - Small Computer Systems Interface
            * **SAS** - Serial Attached SCSI
            * **SAT** - SCSI-to-ATA Translation (SATA device plugged into a
            SAS port)
            * **CSMI** - Common Storage Management Interface (Intel ICH /
            Matrix RAID)
        Generally this should not be specified to allow auto-detection to occur.
        Otherwise, this value overrides the auto-detected type and could
        produce unexpected or no data.
        """
        self.capacity = None
        """**(str):** Device's user capacity."""
        self.firmware = None
        """**(str):** Device's firmware version."""
        self.supports_smart = False
        """
        **(bool):** True if the device supports SMART (or SCSI equivalent) and
        has the feature set enabled. False otherwise.
        """
        self.assessment = None
        """**(str):** SMART health self-assessment as reported by the device."""
        self.messages = []
        """
        **(list of str):** Contains any SMART warnings or other error messages
        reported by the device (ie: ASCQ codes).
        """
        self.is_ssd = None
        """
        **(bool):** True if this device is a Solid State Drive.
        False otherwise.
        """
        self.attributes = [None] * 256
        """
        **(list of `Attribute`):** Contains the complete SMART table information
        for this device, as provided by smartctl. Indexed by attribute #,
        values are set to 'None' for attributes not suported by this device.
        """
        self.tests = []
        """
        **(list of `Log_Entry`):** Contains the complete SMART self-test log
        for this device, as provided by smartctl. If no SMART self-tests have
        been recorded, contains a `None` type instead.
        """
        self._test_running = False
        """
        **(bool):** True if a self-test is currently being run. False otherwise.
        """
        self._test_ECD = None
        """
        **(str):** Estimated completion time of the running SMART selftest.
        Not provided by SAS/SCSI devices.
        """
        self.diags = {}
        """
        **(dict of str):** Contains parsed and processed diagnostic information
        extracted from the SMART information. Currently only populated for
        SAS and SCSI devices, since ATA/SATA SMART attributes are manufacturer
        proprietary.
        """
        if self.name is None:
            warnings.warn("\nDevice '{0}' does not exist! "
                          "This object should be destroyed.".format(name))
            return
        # If no interface type was provided, scan for the device
        elif self.interface is None:
            _grep = 'find' if OS == 'Windows' else 'grep'
            cmd = Popen('smartctl --scan-open | {0} "{1}"'.format(
                _grep, self.name), shell=True, stdout=PIPE, stderr=PIPE)
            _stdout, _stderr = cmd.communicate()
            if _stdout != '':
                scan_string = _stdout.split(' ')
                if scan_string[0] == '#':
                    self.interface = scan_string[3]
                else:
                    self.interface = scan_string[2]
                # Disambiguate the generic interface to a specific type
                self._classify()
            else:
                warnings.warn("\nDevice '{0}' does not exist! "
                              "This object should be destroyed.".format(name))
                return
        # If a valid device was detected, populate its information
        if self.interface is not None:
            self.update()

    def __repr__(self):
        """Define a basic representation of the class object."""
        return "<%s device on /dev/%s mod:%s sn:%s>" % (
            self.interface.upper(), self.name, self.model, self.serial)

    def _check_raid(self, raid_card, raid_params):
        """Check raid card and parameters"""
        if raid_card:
            if raid_card not in ["3ware", "megaraid", "areca",
                                 "aacraid", "cciss", "hpt", "marvell"]:
                warnings.warn("\n{0} raid card is not supported.".format(raid_card))
                return
        params = ''
        if raid_card == 'areca':
            if raid_params:
                try:
                    n = int(raid_params[0])
                    e = int(raid_params[1])
                    params = ",{0}/{1}".format(n, e)
                except:
                    warnings.warn("\nraid card paramter is error.")
                    return
            else:
                return
        if raid_card == 'hpt':
            if raid_params:
                try:
                    l = int(raid_params[0])
                    m = int(raid_params[1])
                    n = int(raid_params[2])
                    params = ",{0}/{1}/{2}".format(l, m, n)
                except:
                    warnings.warn("\nraid card paramter is error.")
                    return
            else:
                return
        if raid_card == 'aacraid':
            if raid_params:
                try:
                    h = int(raid_params[0])
                    l = int(raid_params[1])
                    _id = int(raid_params[2])
                    params = ",{0},{1},{2}".format(h, l, _id)
                except:
                    warnings.warn("\nraid card paramter is error.")
                    return
            else:
                return
        if raid_card in ["3ware", "megaraid", "cciss"]:
            if raid_params:
                try:
                    n = int(raid_params[0])
                    params = ",{0}".format(n)
                except:
                    warnings.warn("\nraid card paramter is error.")
                    return
            else:
                warnings.warn("\nraid card paramter is error.")
                return
        self._raid_type = raid_card
        self._raid_params = str(raid_card) + params

    def all_attributes(self):
        """
        Prints the entire SMART attribute table, in a format similar to
        the output of smartctl.
        """
        header_printed = False
        for attr in self.attributes:
            if attr is not None:
                if not header_printed:
                    print("{0:>3} {1:24}{2:4}{3:4}{4:4}{5:9}{6:8}{7:12}"
                          "{8}".format(
                              'ID#', 'ATTRIBUTE_NAME', 'CUR', 'WST', 'THR',
                              'TYPE', 'UPDATED', 'WHEN_FAIL', 'RAW'))
                    header_printed = True
                print(attr)
        if not header_printed:
            print("This device does not support SMART attributes.")

    def all_selftests(self):
        """
        Prints the entire SMART self-test log, in a format similar to
        the output of smartctl.
        """
        if self.tests is not None:
            if smartctl_type[self.interface] == 'scsi':
                print("{0:3}{1:17}{2:23}{3:7}{4:14}{5:15}".format(
                    'ID', 'Test Description', 'Status', 'Hours',
                    '1st_Error@LBA', '[SK  ASC  ASCQ]'))
            else:
                print("{0:3}{1:17}{2:30}{3:5}{4:7}{5:17}".format(
                    'ID', 'Test_Description', 'Status', 'Left', 'Hours',
                    '1st_Error@LBA'))
            for test in self.tests:
                print(test)
        else:
            print("No self-tests have been logged for this device.")

    def _classify(self):
        """
        Disambiguates generic device types ATA and SCSI into more specific
        ATA, SATA, SAS, SAT and SCSI.
        """
        # SCSI devices might be SCSI, SAS or SAT
        # ATA device might be ATA or SATA
        if self.interface in ['scsi', 'ata']:
            if self.interface == 'scsi':
                test = 'sat'
            else:
                test = 'sata'
            # Look for a SATA PHY to detect SAT and SATA
            if self._raid_type:
                cmd = Popen('smartctl -d {0} -l sataphy {1}/dev/{2}'.format(
                    self._raid_params, self.prefix, self.name), shell=True,
                            stdout=PIPE, stderr=PIPE)
            else:
                cmd = Popen('smartctl -d {0} -l sataphy {1}/dev/{2}'.format(
                    smartctl_type[test], self.prefix, self.name), shell=True,
                            stdout=PIPE, stderr=PIPE)
            _stdout, _stderr = cmd.communicate()
            if 'GP Log 0x11' in _stdout.split('\n')[3]:
                self.interface = test
        # If device type is still SCSI (not changed to SAT above), then
        # check for a SAS PHY
        if self.interface == 'scsi':
            if self._raid_type:
                cmd = Popen('smartctl -d {0} -l sasphy {1}/dev/{2}'.format(
                    self._raid_params, self.prefix, self.name), shell=True, stdout=PIPE, stderr=PIPE)
            else:
                cmd = Popen('smartctl -d scsi -l sasphy {0}/dev/{1}'.format(
                    self.prefix, self.name), shell=True, stdout=PIPE, stderr=PIPE)
            _stdout, _stderr = cmd.communicate()
            if 'SAS SSP' in _stdout.split('\n')[4]:
                self.interface = 'sas'
            # Some older SAS devices do not support the SAS PHY log command.
            # For these, see if smartmontools reports a transport protocol.
            else:
                if self._raid_type:
                    cmd = Popen('smartctl -d {0} -a {1}/dev/{2}'.format(
                        self._raid_params, self.prefix, self.name), shell=True, stdout=PIPE, stderr=PIPE)
                else:
                    cmd = Popen('smartctl -d scsi -a {0}/dev/{1}'.format(
                        self.prefix, self.name), shell=True, stdout=PIPE, stderr=PIPE)
                _stdout, _stderr = cmd.communicate()
                for line in _stdout.split('\n'):
                    if 'Transport protocol' in line and 'SAS' in line:
                        self.interface = 'sas'

    def get_selftest_result(self, output=None):
        """
        Refreshes a device's `pySMART.device.Device.tests` attribute to obtain
        the latest test results. If a new test result is obtained, its content
        is returned.

        ###Args:
        * **output (str, optional):** If set to 'str', the string
        representation of the most recent test result will be returned, instead
        of a `Test_Entry` object.

        ##Returns:
        * **(int):** Return status code. One of the following:
            * 0 - Success. Object (or optionally, string rep) is attached.
            * 1 - Self-test in progress. Must wait for it to finish.
            * 2 - No new test results.
        * **(`Test_Entry` or str):** Most recent `Test_Entry` object (or
        optionally it's string representation) if new data exists.  Status
        message string on failure.
        * **(str):** Estimated completion time of a test in-progess, if known.
        Otherwise 'None'.
        """
        # SCSI self-test logs hold 20 entries while ATA logs hold 21
        if smartctl_type[self.interface] == 'scsi':
            maxlog = 20
        else:
            maxlog = 21
        # If we looked only at the most recent test result we could be fooled
        # by two short tests run close together (within the same hour) appearing
        # identical. Comparing the length of the log adds some confidence until
        # it maxes, as above. Comparing the least-recent test result greatly
        # diminishes the chances that two sets of two tests each were run within
        # an hour of themselves, but with 16-17 other tests run in between them.
        if self.tests is not None:
            _first_entry = self.tests[0]
            _len = len(self.tests)
            _last_entry = self.tests[_len - 1]
        else:
            _len = 0
        self.update()
        # Check whether the list got longer (ie: new entry)
        if self.tests is not None and len(self.tests) != _len:
            # If so, for ATA, return the newest test result
            if not ('in progress' in self.tests[0].status or
                    'NOW' in self.tests[0].hours):
                self._test_running = False
                self._test_ECD = None
                if output == 'str':
                    return (0, str(self.tests[0]), None)
                else:
                    return (0, self.tests[0], None)
            else:
                self._test_running = True
        elif _len == maxlog:
            # If not, because it's max size already, check for new entries
            if ((_first_entry.type != self.tests[0].type or
                    _first_entry.hours != self.tests[0].hours or
                    _last_entry.type != self.tests[len(self.tests) - 1].type or
                    _last_entry.hours != self.tests[len(self.tests) - 1].hours)
                and not 'NOW' in self.tests[0].hours):
                self._test_running = False
                self._test_ECD = None
                if output == 'str':
                    return (0, str(self.tests[0]), None)
                else:
                    return (0, self.tests[0], None)
            else:
                if 'NOW' in self.tests[0].hours:
                    self._test_running = True
                # If nothing new was found, see if we know of a running test.
                if self._test_running:
                    if (not ('in progress' in self.tests[0].status or
                             'NOW' in self.tests[0].hours) and
                            smartctl_type[self.interface] == 'scsi'):
                        self._test_running = False
                        self._test_ECD = None
                        if output == 'str':
                            return (0, str(self.tests[0]), None)
                        else:
                            return (0, self.tests[0], None)
                    else:
                        return (1, 'Self-test in progress. Please wait.',
                                self._test_ECD)
                else:
                    return (2, 'No new self-test results found.', None)
        else:
            # If log is still empty, or did not get longer, see whether we
            # know of a running test.
            if self._test_running:
                if (not ('in progress' in self.tests[0].status or
                         'NOW' in self.tests[0].hours) and
                        smartctl_type[self.interface] == 'scsi'):
                    self._test_running = False
                    self._test_ECD = None
                    if output == 'str':
                        return (0, str(self.tests[0]), None)
                    else:
                        return (0, self.tests[0], None)
                else:
                    return (1, 'Self-test in progress. Please wait.',
                            self._test_ECD)
            else:
                return (2, 'No new self-test results found.', None)

    def _guess_SMART_type(self, line):
        """
        This function is not used in the generic wrapper, however the header
        is defined so that it can be monkey-patched by another application.
        """
        pass

    def _make_SMART_warnings(self):
        """
        Parses an ATA/SATA SMART table for attributes with the 'when_failed'
        value set. Generates an warning message for any such attributes and
        updates the self-assessment value if necessary.
        """
        if smartctl_type[self.interface] == 'scsi':
            return
        for attr in self.attributes:
            if attr is not None:
                if attr.when_failed == 'In_the_past':
                    self.messages.append("".join(
                        [attr.name, " failed in the past with value ",
                         attr.worst, ". [Threshold: ", attr.thresh, ']']))
                    if not self.assessment == 'FAIL':
                        self.assessment = 'WARN'
                elif attr.when_failed == 'FAILING_NOW':
                    self.assessment = 'FAIL'
                    self.messages.append("".join(
                        [attr.name, " is failing now with value ",
                         attr.value, ". [Threshold: ", attr.thresh, ']']))
                elif not attr.when_failed == '-':
                    self.messages.append("".join(
                        [attr.name, " says it failed '", attr.when_failed,
                         "'. [V=", attr.value, ",W=", attr.worst, ",T=",
                         attr.thresh, ']']))
                    if not self.assessment == 'FAIL':
                        self.assessment = 'WARN'

    def run_selftest(self, test_type):
        """
        Instructs a device to begin a SMART self-test. All tests are run in
        'offline' / 'background' mode, allowing normal use of the device while
        it is being tested.

        ##Args:
        * **test_type (str):** The type of test to run. Accepts the following
        (not case sensitive):
            * **short** - Brief electo-mechanical functionality check.
            Generally takes 2 minutes or less.
            * **long** - Thorough electro-mechanical functionality check,
            including complete recording media scan. Generally takes several
            hours.
            * **conveyance** - Brief test used to identify damage incurred in
            shipping. Generally takes 5 minutes or less. **This test is not
            supported by SAS or SCSI devices.**

        ##Returns:
        * **(int):** Return status code.  One of the following:
            * 0 - Self-test initiated successfully
            * 1 - Previous self-test running. Must wait for it to finish.
            * 2 - Unknown or illegal test type requested.
            * 3 - Unspecified smartctl error. Self-test not initiated.
        * **(str):** Return status message.
        * **(str):** Estimated self-test completion time if a test is started.
        Otherwise 'None'.
        """
        if self._test_running:
            return (1, 'Self-test already in progress. Please wait.',
                    self._test_ECD)
        if test_type.lower() in ['short', 'long', 'conveyance']:
            if (test_type.lower() == 'conveyance' and
                    smartctl_type[self.interface] == 'scsi'):
                return (2, "Cannot perform 'conveyance' test on SAS/SCSI "
                        "devices.", None)
            if self._raid_type:
                cmd = Popen('smartctl -d {0} -t {1} {2}/dev/{3}'.format(
                    self._raid_params, test_type, self.prefix, self.name),
                            shell=True, stdout=PIPE, stderr=PIPE)                
            else:
                cmd = Popen('smartctl -d {0} -t {1} {2}/dev/{3}'.format(
                    smartctl_type[self.interface], test_type, self.prefix, self.name),
                            shell=True, stdout=PIPE, stderr=PIPE)
            _stdout, _stderr = cmd.communicate()
            _success = False
            _running = False
            for line in _stdout.split('\n'):
                if 'has begun' in line:
                    _success = True
                    self._test_running = True
                if 'aborting current test' in line:
                    _running = True
                if _success and 'complete after' in line:
                    self._test_ECD = line[25:].rstrip()
            if _success:
                return (0, "Self-test started successfully", self._test_ECD)
            else:
                if _running:
                    return (1, 'Self-test already in progress. Please wait.',
                            self._test_ECD)
                else:
                    return (3, 'Unspecified Error. Self-test not started.',
                            None)
        else:
            return (2, "Unknown test type '{0}' requested.".format(test_type),
                    None)

    def update(self):
        """
        Queries for device information using smartctl and updates all
        class members, including the SMART attribute table and self-test log.
        Can be called at any time to refresh the `pySMART.device.Device`
        object's data content.
        """
        if self._raid_type:
            cmd = Popen('smartctl -d {0} -a {1}/dev/{2}'.format(
                self._raid_params, self.prefix, self.name), shell=True,
                        stdout=PIPE, stderr=PIPE)
        else:
            cmd = Popen('smartctl -d {0} -a {1}/dev/{2}'.format(
                smartctl_type[self.interface], self.prefix, self.name), shell=True,
                        stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = cmd.communicate()
        parse_self_tests = False
        parse_ascq = False
        self.tests = []
        for line in _stdout.split('\n'):
            if line.strip() == '':  # Blank line stops sub-captures
                if parse_self_tests == True:
                    parse_self_tests = False
                    if len(self.tests) == 0:
                        self.tests = None
                if parse_ascq:
                    parse_ascq = False
                    self.messages.append(message)
            if parse_ascq:
                message += ' ' + line.lstrip().rstrip()
            if parse_self_tests:
                num = line[1:3]
                if smartctl_type[self.interface] == 'scsi':
                    format = 'scsi'
                    test_type = line[5:23].rstrip()
                    status = line[23:46].rstrip()
                    segment = line[46:55].lstrip().rstrip()
                    hours = line[55:65].lstrip().rstrip()
                    LBA = line[65:78].lstrip().rstrip()
                    line_ = ' '.join(line.split('[')[1].split()).split(' ')
                    sense = line_[0]
                    ASC = line_[1]
                    try:
                        ASCQ = line_[2][:-1]
                    except:
                        ASCQ = '-'
                    self.tests.append(Test_Entry(
                        format, num, test_type, status, hours, LBA,
                        segment=segment, sense=sense, ASC=ASC, ASCQ=ASCQ))
                else:
                    format = 'ata'
                    test_type = line[5:25].rstrip()
                    status = line[25:54].rstrip()
                    remain = line[54:58].lstrip().rstrip()
                    hours = line[60:68].lstrip().rstrip()
                    LBA = line[77:].rstrip()
                    self.tests.append(Test_Entry(
                        format, num, test_type, status, hours, LBA,
                        remain=remain))
            # Basic device information parsing
            if 'Vendor:' in line:
                self.vendor = line.split(':')[1].lstrip().rstrip()
                self._guess_SMART_type(line.lower())
            if 'Transport protocol' in line:
                self.transport_protocol = line.split(':')[1].lstrip().rstrip()
                self._guess_SMART_type(line.lower())
            if 'SATA Version is' in line:
                version = line.split(':', 1)[1]
                self.sata_version = version.lstrip().rstrip()
            if 'Sector Size' in line:
                self.sector_size = line.split(':')[1].lstrip().rstrip()
            if 'Model Family' in line:
                self._guess_SMART_type(line.lower())
            if 'Device Model' in line or 'Product' in line:
                self.model = line.split(':')[1].lstrip().rstrip()
                self._guess_SMART_type(line.lower())
            if 'Serial Number' in line or 'Serial number' in line:
                self.serial = line.split(':')[1].split()[0].rstrip()
            if 'LU WWN' in line:
                self._guess_SMART_type(line.lower())
            if 'Firmware Version' in line or 'Revision' in line:
                self.firmware = line.split(':')[1].lstrip().rstrip()
            if 'User Capacity' in line:
                self.capacity = (
                    #line.replace(']', '[').split('[')[1].lstrip().rstrip()
                    line.split()[2].replace(',', '')
                )
            if 'SMART support' in line:
                self.supports_smart = 'Enabled' in line
            if 'does not support SMART' in line:
                self.supports_smart = False
            if 'Rotation Rate' in line:
                if 'Solid State Device' in line:
                    self.is_ssd = True
                elif 'rpm' in line:
                    self.is_ssd = False
            if 'SMART overall-health self-assessment' in line:  # ATA devices
                if line.split(':')[1].strip() == 'PASSED':
                    self.assessment = 'PASS'
                else:
                    self.assessment = 'FAIL'
            if 'SMART Health Status' in line:  # SCSI devices
                if line.split(':')[1].strip() == 'OK':
                    self.smart_health_status = 'OK'
                    self.assessment = 'PASS'
                else:
                    self.smart_health_status = 'FAIL'
                    self.assessment = 'FAIL'
                    parse_ascq = True  # Set flag to capture status message
                    message = line.split(':')[1].lstrip().rstrip()
            # SMART Attribute table parsing
            if '0x0' in line and '_' in line:
                # Replace multiple space separators with a single space, then
                # tokenize the string on space delimiters
                line_ = ' '.join(line.split()).split(' ')
                if not '' in line_:
                    self.attributes[int(line_[0])] = Attribute(
                        line_[0], line_[1], line[2], line_[3], line_[4],
                        line_[5], line_[6], line_[7], line_[8], line_[9])
            if 'Description' in line and '(hours)' in line:
                parse_self_tests = True  # Set flag to capture test entries
            if 'No self-tests have been logged' in line:
                self.tests = None
            # Everything from here on is parsing SCSI information that takes
            # the place of similar ATA SMART information
            if 'used endurance' in line:
                pct = int(line.split(':')[1].strip()[:-1])
                self.diags['Life_Left'] = str(100 - pct) + '%'
                self.percent_used_indicator = str(pct)
            if 'Current Drive Temperature' in line:
                temp = int(line.split(':')[1].strip()[:-1])
                self.current_drive_temp = temp
            if 'Drive Trip Temperature' in line:
                temp = int(line.split(':')[1].strip()[:-1])
                self.drive_trip_temp = temp
            if 'Specified cycle count' in line:
                lifetime = line.split(':')[1].strip()
                self.spec_cycle_count_over_lifetime = lifetime
                self.diags['Start_Stop_Spec'] = lifetime
                if self.diags['Start_Stop_Spec'] == '0':
                    self.diags['Start_Stop_Pct_Left'] = '-'
            if 'Accumulated start-stop cycles' in line:
                start_stop_cycles = line.split(':')[1].strip()
                self.accumulated_start_stop_cycles = start_stop_cycles
                self.diags['Start_Stop_Cycles'] = start_stop_cycles
                if not 'Start_Stop_Pct_Left' in self.diags:
                    self.diags['Start_Stop_Pct_Left'] = str(int(round(
                        100 - (int(self.diags['Start_Stop_Cycles']) /
                               int(self.diags['Start_Stop_Spec'])), 0))) + '%'
            if 'Specified load-unload count' in line:
                self.diags['Load_Cycle_Spec'] = line.split(':')[1].strip()
                if self.diags['Load_Cycle_Spec'] == '0':
                    self.diags['Load_Cycle_Pct_Left'] = '-'
            if 'Accumulated load-unload cycles' in line:
                self.diags['Load_Cycle_Count'] = line.split(':')[1].strip()
                if not 'Load_Cycle_Pct_Left' in self.diags:
                    self.diags['Load_Cycle_Pct_Left'] = str(int(round(
                        100 - (int(self.diags['Load_Cycle_Count']) /
                               int(self.diags['Load_Cycle_Spec'])), 0))) + '%'
            if 'Elements in grown defect list' in line:
                element_in_grown_defect_list = line.split(':')[1].strip()
                self.element_in_grown_defect_list = element_in_grown_defect_list
                self.diags['Reallocated_Sector_Ct'] = element_in_grown_defect_list
            # Cache Information
            if 'Blocks sent to initiator' in line:
                self.blocks_sent_to_initiator = line.split('=')[1].strip()
            if 'Blocks received from initiator' in line:
                self.blocks_received_from_initiator = line.split('=')[1].strip()
            # Factory Information
            if 'number of hours powered up' in line:
                self.power_up_hours = line.split('=')[1].strip()
            # Error counter log
            if 'read:' in line and smartctl_type[self.interface] == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                self.diags['ErrorsCorrectedbyECCFastRead'] = line_[1]
                self.diags['ErrorsCorrectedbyECCDelayedRead'] = line_[2]
                self.diags['ErrorCorrectedByRereadsRewritesRead'] = line_[3]
                self.diags['TotalErrorsCorrectedRead'] = line_[4]
                self.diags['CorrectionAlgorithmInvocationsRead'] = line_[5]
                self.diags['GigaBytesProcessedRead'] = line_[6]
                self.diags['TotalUncorrectedErrorsRead'] = line_[7]
            if 'write:' in line and smartctl_type[self.interface] == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                self.diags['ErrorsCorrectedbyECCFastWrite'] = line_[1]
                self.diags['ErrorsCorrectedbyECCDelayedWrite'] = line_[2]
                self.diags['ErrorCorrectedByRereadsRewritesWrite'] = line_[3]
                self.diags['TotalErrorsCorrectedWrite'] = line_[4]
                self.diags['CorrectionAlgorithmInvocationsWrite'] = line_[5]
                self.diags['GigaBytesProcessedWrite'] = line_[6]
                self.diags['TotalUncorrectedErrorsWrite'] = line_[7]
            if 'verify:' in line and smartctl_type[self.interface] == 'scsi':
                line_ = ' '.join(line.split()).split(' ')
                self.diags['ErrorsCorrectedbyECCFastVerify'] = line_[1]
                self.diags['ErrorsCorrectedbyECCDelayedVerify'] = line_[2]
                self.diags['ErrorCorrectedByRereadsRewritesVerify'] = line_[3]
                self.diags['TotalErrorsCorrectedVerify'] = line_[4]
                self.diags['CorrectionAlgorithmInvocationsVerify'] = line_[5]
                self.diags['GigaBytesProcessedVerify'] = line_[6]
                self.diags['TotalUncorrectedErrorsVerify'] = line_[7]
            if 'non-medium error count' in line:
                self.diags['Non-Medium_Errors'] = line.split(':')[1].strip()
            if 'Accumulated power on time' in line:
                self.diags['Power_On_Hours'] = line.split(':')[1].split(' ')[1]
        if not smartctl_type[self.interface] == 'scsi':
            # Parse the SMART table for below-threshold attributes and create
            # corresponding warnings for non-SCSI disks
            self._make_SMART_warnings()
        else:
            # For SCSI disks, any diagnostic attribute which was not captured
            # above gets set to '-' to indicate unsupported/unavailable.
            for diag in ['ErrorsCorrectedbyECCFastRead', 'ErrorsCorrectedbyECCDelayedRead',
                         'ErrorCorrectedByRereadsRewritesRead', 'TotalErrorsCorrectedRead',
                         'CorrectionAlgorithmInvocationsRead', 'GigaBytesProcessedRead',
                         'TotalUncorrectedErrorsRead', 
                         'ErrorsCorrectedbyECCFastWrite', 'ErrorsCorrectedbyECCDelayedWrite',
                         'ErrorCorrectedByRereadsRewritesWrite', 'TotalErrorsCorrectedWrite',
                         'CorrectionAlgorithmInvocationsWrite', 'GigaBytesProcessedWrite',
                         'TotalUncorrectedErrorsWrite',
                         'ErrorsCorrectedbyECCFastVerify', 'ErrorsCorrectedbyECCDelayedVerify',
                         'ErrorCorrectedByRereadsRewritesVerify', 'TotalErrorsCorrectedVerify',
                         'CorrectionAlgorithmInvocationsVerify', 'GigaBytesProcessedVerify',
                         'TotalUncorrectedErrorsVerify', 'Reallocated_Sector_Ct',
                         'Start_Stop_Spec', 'Start_Stop_Cycles',
                         'Load_Cycle_Spec', 'Load_Cycle_Count',
                         'Start_Stop_Pct_Left', 'Load_Cycle_Pct_Left',
                         'Power_On_Hours', 'Life_Left', 'Non-Medium_Errors']:
                if not diag in self.diags:
                    self.diags[diag] = '-'
            # If not obtained above, make a direct attempt to extract power on
            # hours from the background scan results log.
            if self.diags['Power_On_Hours'] == '-':
                if self._raid_type:
                    cmd = Popen('smartctl -d {0} -l background {1}/dev/{2}'.format(
                        self._raid_params, self.prefix, self.name), shell=True,
                                stdout=PIPE, stderr=PIPE)
                else:
                    cmd = Popen('smartctl -d scsi -l background {0}/dev/{1}'.format(
                        self.prefix, self.name), shell=True,
                                stdout=PIPE, stderr=PIPE)
                _stdout, _stderr = cmd.communicate()
                for line in _stdout.split('\n'):
                    if 'power on time' in line:
                        hour_str = line.split(':')[1].split(' ')[1]
                        self.power_up_hours = hour_str
                        self.diags['Power_On_Hours'] = hour_str

__all__ = ['Device']
