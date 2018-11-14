from __future__ import absolute_import

import os
import time
import logging

from . import smart_metrics


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)

DEFAULT_INTERVAL = 10
DEFAULT_PORT = 9110
DEFAULT_DEVPATH = '/dev'


def main():
    from prometheus_client import start_http_server
    try:
        hostdev_path = os.environ.get('HOSTDEV_PATH', DEFAULT_DEVPATH)
        smart_port = os.environ.get('SMART_PORT', DEFAULT_PORT)
        interval = os.environ.get('INTERVAL_TIME', DEFAULT_INTERVAL) 

        print "Start smart exporter daemon..."
        start_http_server(int(smart_port))

        plugin1 = smart_metrics.SaiDisk_Smart_Plugin(hostdev_path)
        plugin2 = smart_metrics.SaiDisk_Plugin(hostdev_path)
        while True:
            plugin1.collect_data()
            plugin2.collect_data()
            time.sleep(int(interval))
    except KeyboardInterrupt:
        print "Exit"
    except Exception as e:
        print str(e)
