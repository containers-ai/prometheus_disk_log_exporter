from __future__ import absolute_import
import logging

from prometheus_client import Gauge

from smart_exporter.lib.smart import Smartctl


_logger = logging.getLogger(__name__)

SAI_DISK_SMART_FILE = '/tmp/sai_disk_smart.prom'
SAI_DISK_FILE = '/tmp/sai_disk.prom'


def getall_diskpath(path='/dev'):
    import os
    import stat
    result = []
    scsi_majors = set([
        8, 65, 66, 67, 68, 69, 70, 71,
        128, 129, 130, 131, 132, 133, 134, 135])

    for f in os.listdir(path):
        if 'initctl' in f:
            continue
        fp = os.path.join(path, f)
        info = os.stat(fp)
        if not stat.S_ISBLK(info.st_mode):
            continue
        major = os.major(info.st_rdev)
        minor = os.minor(info.st_rdev)
        if major in scsi_majors and divmod(minor, 16)[1] is 0:
            result.append(fp)
    return result


class SaiDisk_Plugin(object):
    def __init__(self, path):
        self.disks = getall_diskpath(path)
        self.metrics = dict()

    def collect_data(self):
        if not self.disks:
            return

        base_metric = 'sai_disk'
        header = ['disk_name', 'disk_wwn']

        metrics = self.metrics
        for path in self.disks:
            disk_name = path.split('/')[-1]
            smart = Smartctl(path)
            serial = smart.get_serial_number()

            if serial:
                values = [disk_name, serial]
                field_name = 'serial_number'
                ext_header = header + [field_name]
                ext_values = values + [serial]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else: 
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()
            else:
                values = [disk_name, '']

            firmware_version = smart.get_firmware_version()
            if firmware_version:
                field_name = 'firmware_version'
                ext_header = header + [field_name]
                ext_values = values + [firmware_version]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            model = smart.get_model()
            if model:
                field_name = 'model'
                ext_header = header + [field_name]
                ext_values = values + [model]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            sata_version = smart.get_sata_version()
            if sata_version:
                field_name = 'sata_version'
                ext_header = header + [field_name]
                ext_values = values + [sata_version]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            sector_size = smart.get_sector_size()
            if sector_size:
                field_name = 'sector_size'
                ext_header = header + [field_name]
                ext_values = values + [sector_size]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            size = smart.get_capacity()
            if size:
                field_name = 'size'
                ext_header = header + [field_name]
                ext_values = values + [size]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            transport_protocol = smart.get_transport_protocol()
            if transport_protocol:
                field_name = 'transport_protocol'
                ext_header = header + [field_name]
                ext_values = values + [transport_protocol]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            vendor = smart.get_vendor()
            if vendor:
                field_name = 'vendor'
                ext_header = header + [field_name]
                ext_values = values + [vendor]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()

            disk_type = smart.get_disk_type()
            if disk_type:
                field_name = 'disk_type'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header,)
                    metrics[metric] = gauge
                gauge.labels(*values).set(disk_type)

            disk_status = 1
            if disk_status:
                field_name = 'disk_status'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(disk_status)


class SaiDisk_Smart_Plugin(object):
    def __init__(self, path):
        self.disks = getall_diskpath(path)
        self.metrics = dict()

    def collect_data(self):
        if not self.disks:
            return

        base_metric = 'sai_disk_smart'
        header = ['disk_name', 'disk_wwn']

        metrics = self.metrics
        for path in self.disks:
            disk_name = path.split('/')[-1]
            smart = Smartctl(path)
            serial = smart.get_serial_number()

            if serial:
                values = [disk_name, serial]
                field_name = 'serial'
                ext_header = header + [field_name]
                ext_values = values + [serial]
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else: 
                    gauge = Gauge(metric, field_name, ext_header)
                    metrics[metric] = gauge
                gauge.labels(*ext_values).inc()
            else:
                values = [disk_name, '']

            attrs = smart.device.attributes
            spec_rawlist = []
            for num, attr in enumerate(attrs):
                if not attr:
                    continue
                raw = attr.raw
                try:
                    data = int(float(raw))
                except:
                    data = None
                if data is not None:
                    field_name = "%s_raw" % (num, )
                    metric = "%s_%s" % (base_metric, field_name)
                    if metric in metrics:
                        gauge = metrics[metric]
                    else:
                        gauge = Gauge(metric, field_name, header)
                        metrics[metric] = gauge
                    gauge.labels(*values).set(data)
                    if num in [9, 241, 242]:
                        spec_rawlist.append(num)

            power_up_hours = smart.get_power_up_hours()
            if power_up_hours and 9 not in spec_rawlist:
                data = int(float(power_up_hours))
                field_name = '9_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            blocks_received_from_initiator = \
                smart.get_blocks_received_from_initiator()
            if blocks_received_from_initiator and 241 not in spec_rawlist:
                data = int(blocks_received_from_initiator)
                field_name = '241_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            blocks_send_to_initiator = \
                smart.get_blocks_send_to_initiator()
            if blocks_send_to_initiator and 242 not in spec_rawlist:
                data = int(blocks_send_to_initiator)
                field_name = '241_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            percent_used_indicator = smart.get_percent_used_indicator()
            if percent_used_indicator:
                data = percent_used_indicator
                field_name = 'PercentageUsedEnduranceIndicator_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            current_drive_temp = smart.get_current_drive_temp()
            if current_drive_temp:
                data = current_drive_temp
                field_name = 'CurrentDriveTemperature_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            drive_trip_temp = smart.get_drive_trip_temp()
            if drive_trip_temp:
                data = drive_trip_temp
                field_name = 'DriveTripTemperature_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)

            element_in_grown_defect_list = smart.get_element_in_grown_defect_list()
            if element_in_grown_defect_list:
                data = element_in_grown_defect_list
                field_name = 'ElementsInGrownDefectList_raw'
                metric = "%s_%s" % (base_metric, field_name)
                if metric in metrics:
                    gauge = metrics[metric]
                else:
                    gauge = Gauge(metric, field_name, header)
                    metrics[metric] = gauge
                gauge.labels(*values).set(data)
            
            for field_name in ['CorrectionAlgorithmInvocationsRead_raw',
                               'CorrectionAlgorithmInvocationsWrite_raw',
                               'ErrorCorrectedByRereadsRewritesRead_raw',
                               'ErrorCorrectedByRereadsRewritesWrite_raw',
                               'ErrorsCorrectedbyECCDelayedRead_raw',
                               'ErrorsCorrectedbyECCDelayedWrite_raw',
                               'ErrorsCorrectedbyECCFastRead_raw',
                               'ErrorsCorrectedbyECCFastWrite_raw',
                               'GigaBytesProcessedRead_raw',
                               'GigaBytesProcessedWrite_raw',
                               'TotalErrorsCorrectedRead_raw',
                               'TotalErrorsCorrectedWrite_raw',
                               'TotalUncorrectedErrorsRead_raw',
                               'TotalUncorrectedErrorsWrite_raw']:
                data = smart.get_error_counter_log(field_name)
                if data is not None:
                    metric = "%s_%s" % (base_metric, field_name)
                    if metric in metrics:
                        gauge = metrics[metric]
                    else:
                        gauge = Gauge(metric, field_name, header)
                        metrics[metric] = gauge
                    gauge.labels(*values).set(data)

