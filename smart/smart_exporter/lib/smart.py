from __future__ import absolute_import
from smart_exporter.lib.pySMART import Device


GiB = 1000 * 1000 * 1000


class Smartctl(object):
    """ DiskProphet smartctl manager """
    def __init__(self, dev_name, interface=None,
                 raid_card=None, raid_params=[]):
        self.device = None
        self.dev_name = dev_name
        self.interface = interface
        self.raid_card = raid_card
        self.raid_params = raid_params
        if self.interface:
            self.device = Device(self.dev_name, self.interface,
                                 self.raid_card, self.raid_params)
        else:
            self.device = Device(self.dev_name)

    def get_disk_type(self):
        """ return type:
            0: "Unknown", 1: "HDD",
            2: "SSD",     3: "SSD NVME",
            4: "SSD SAS", 5: "SSD SATA",
            6: "HDD SAS", 7: "HDD SATA"
        """
        disk_type = 0
        if self.device.is_ssd:
            if self.get_sata_version() and not self.get_transport_protocol():
                disk_type = 5
            elif 'SCSI'.lower() in self.get_transport_protocol().lower():
                disk_type = 4
            elif 'NVMe'.lower() in self.get_transport_protocol().lower():
                disk_type = 3
            else:
                disk_type = 2
        else:
            if self.get_sata_version() and not self.get_transport_protocol():
                disk_type = 7
            elif 'SCSI'.lower() in self.get_transport_protocol().lower():
                disk_type = 6
            else:
                disk_type = 1
        return disk_type

    def get_firmware_version(self):
        return self.device.firmware if self.device.firmware else ''

    def get_sata_version(self):
        return self.device.sata_version if self.device.sata_version else ''

    def get_model(self):
        return self.device.model if self.device.model else ''

    def get_sector_size(self):
        if self.device.sector_size:
            return self.device.sector_size
        return '512'

    def get_serial_number(self):
        if self.device.serial:
            return self.device.serial
        return ''

    def get_capacity(self):
        try:
            capacity = int(self.device.capacity)
        except:
            return ''
        return str(capacity / GiB) + 'G'

    def get_smart_health_status(self):
        if self.device.smart_health_status:
            return self.device.smart_health_status
        return ''

    def get_transport_protocol(self):
        if self.device.transport_protocol:
            return self.device.transport_protocol
        return ''

    def get_vendor(self):
        return self.device.vendor if self.device.vendor else ''

    def get_raw_data(self, num):
        try:
            raw = self.device.attributes[num].raw
            data = int(float(raw))
        except:
            data = None
        return data

    def get_percent_used_indicator(self):
        try:
            data = int(self.device.percent_used_indicator)
        except:
            data = None
        return data

    def get_error_counter_log(self, name):
        data = None
        diags = self.device.diags
        pattern = name.split('_')[0]
        if diags.get(pattern):
            try:
                if name in ['GigaBytesProcessedRead_raw',
                            'GigaBytesProcessedWrite_raw']:
                    data = float(diags[pattern])
                else:
                    data = int(float(diags[pattern]))
            except:
                data = None
        return data

    def get_current_drive_temp(self):
        if self.device.current_drive_temp:
            return int(self.device.current_drive_temp)
        return None

    def get_drive_trip_temp(self):
        if self.device.drive_trip_temp:
            return int(self.device.drive_trip_temp)
        return None

    def get_element_in_grown_defect_list(self):
        if self.device.element_in_grown_defect_list:
            return int(float(self.device.element_in_grown_defect_list))
        return None

    def get_power_up_hours(self):
        return self.device.power_up_hours

    def get_blocks_received_from_initiator(self):
        return self.device.blocks_received_from_initiator

    def get_blocks_send_to_initiator(self):
        return self.device.blocks_sent_to_initiator

