from __future__ import absolute_import

import sys
import os


if not __package__:
    path = os.path.join(os.path.dirname(__file__), os.pardir)
    sys.path.insert(0, path)

import smart_exporter
smart_exporter.main()
