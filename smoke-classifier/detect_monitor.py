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

Monitor fire detection process and restart if it dies.
Also restart if the detection process is not making progress.

"""
import time, datetime
import os
import psutil
import subprocess
import psutil
import tempfile

import sys
import settings
sys.path.insert(0, settings.fuegoRoot + '/lib')
import collect_args
import db_manager

def findProcess(name):
    for proc in psutil.process_iter():
        pinfo = None
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'cmdline'])
            matches = list(filter(lambda x: name in x, pinfo['cmdline']))
            if len(matches) > 0:
                # print(matches, pinfo)
                return pinfo['pid']
        except:
            pass
    return None


def startProcess(detectFire, heartbeatFileName):
    pArgs = [
        sys.executable,
        os.path.join(settings.fuegoRoot, "smoke-classifier", detectFire),
        '--heartbeat',
        heartbeatFileName
    ]
    print('Starting', pArgs)
    subprocess.Popen(pArgs)


def lastHeartbeat(heartbeatFileName):
    return os.stat(heartbeatFileName).st_mtime


def lastScoreTimestamp(dbManager):
    sqlStr = "SELECT max(timestamp) from scores"
    dbResult = dbManager.query(sqlStr)
    if len(dbResult) == 1:
        return dbResult[0]['max(timestamp)']
    return 0

def main():
    dbManager = db_manager.DbManager(settings.db_file)
    scriptName = 'detect_fire.py'
    heartbeatFile = tempfile.NamedTemporaryFile()
    heartbeatFileName = heartbeatFile.name
    while True:
        foundPid = findProcess(scriptName)
        if foundPid:
            # lastTS = lastScoreTimestamp(dbManager) # check DB progress
            lastTS = lastHeartbeat(heartbeatFileName) # check heartbeat
            timestamp = int(time.time())
            if (timestamp - lastTS) > 2*60: # warn if stuck more than 2 minutes
                timeStr = datetime.datetime.now().strftime('%F %T')
                print('%s: Process %s: %d seconds since last image scanned' % (timeStr, foundPid, timestamp - lastTS))
            if (timestamp - lastTS) > 5*60: # kill if stuck more than 5 minutes
                proc = psutil.Process(foundPid)
                print('Killing', proc.cmdline())
                proc.kill()
                foundPid = None
        if not foundPid:
            timeStr = datetime.datetime.now().strftime('%F %T')
            print('%s: Process not found' % timeStr)
            startProcess(scriptName, heartbeatFileName)
            time.sleep(2*60) # give couple minutes for startup time
        time.sleep(30)


if __name__=="__main__":
    main()
