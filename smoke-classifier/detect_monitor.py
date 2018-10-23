# Copyright 2018 The Fuego Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""

Monitor fire detection process and restart if it dies

"""
import time, datetime
import os
import psutil
import subprocess

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import collect_args

def findProcess(name):
    for proc in psutil.process_iter():
        pinfo = None
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'cmdline'])
            matches = list(filter(lambda x: name in x, pinfo['cmdline']))
            if len(matches) > 0:
                # print(matches, pinfo)
                return True
        except:
            pass
    return False


def startProcess(name):
    pArgs = [
        sys.executable,
        os.path.join(settings.fuegoRoot, "smoke-classifier", name)
    ]
    print(pArgs)
    subprocess.Popen(pArgs)

def main():
    scriptName = 'detect_fire.py'
    while True:
        found = findProcess(scriptName)
        if not found:
            timestamp = int(time.time())
            timeStr = datetime.datetime.fromtimestamp(timestamp).strftime('%F %T')
            print('%s: Process not found' % timeStr)
            startProcess(scriptName)
        time.sleep(10)


if __name__=="__main__":
    main()
