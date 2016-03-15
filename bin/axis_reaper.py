#!/usr/bin/env python
"""Monitor the Axis collection by looking for books that have been removed."""
import os
import sys
bin_dir = os.path.split(__file__)[0]
package_dir = os.path.join(bin_dir, "..")
sys.path.append(os.path.abspath(package_dir))
from core.scripts import RunMonitorScript
from api.axis import AxisCollectionReaper
RunMonitorScript(AxisCollectionReaper).run()
