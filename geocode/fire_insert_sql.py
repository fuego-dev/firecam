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

Take the output of fire_coords.py and write the data to 'fires' table in sqlite DB
With the fire and camera data in the DB, matches can be found with following query:

select fires.name, (fires.Latitude-cameras.Latitude)*(fires.Latitude-cameras.Latitude)+(fires.Longitude-cameras.Longitude)*(fires.Longitude-cameras.Longitude) as distance, fires.Started, fires.Updated, fires.Url, fires.Location, fires.County, fires.Latitude, fires.Longitude, cameras.Name, cameras.Latitude, cameras.Longitude from fires cross join cameras where fires.started is not null and distance < 0.02 order by distance;
"""

import datetime
import ast
import sys

import settings
print(settings)
print(settings.fuegoRoot)
sys.path.insert(0, settings.fuegoRoot + '/lib')
import db_manager

fileName = '../fires_geocoded.txt'
manager = db_manager.DbManager(settings.fuegoRoot + '/resources/local.db')

lineNumber = 1
skipped=[]
with open(fileName, 'r') as myfile:
    for line in myfile:
        # print("raw", line)
        parsed = ast.literal_eval(line)
        # print("parsed", parsed)
        url = parsed.get('href')
        if (url != None):
            parsed['url'] = url
        parsed.pop('href', None)
        parsed.pop('Extra', None)
        # print("parsed2", lineNumber, parsed)
        lineNumber += 1
        manager.add_data('fires', parsed)


print(skipped)