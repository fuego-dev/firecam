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

Take the output of calfire_parse.py and send the location information to
google's geocoding API to get the latitude and longitude.  Then output
the augmented data.

"""

import ast
import googlemaps

fileName = '../fires_parsed.txt'
key = 'AIzaSyBZ9NnCWPwm6Y7gfXiKJXgi8ha13X295o8' #dkgu-dev
# key = 'AIzaSyBh2KIAcK7ueQrI8dMXT_sW-ICPqtL_O60' #fuego-detect

gmaps = googlemaps.Client(key=key)

lineNumber = 1
skipped=[]
with open(fileName, 'r') as myfile:
    for line in myfile:
        # print("raw", line)
        parsed = ast.literal_eval(line)
        # print("parsed", parsed['Name'], parsed['Location'] + ',' + parsed['County'])
        geocode_result = gmaps.geocode(parsed['Location'] + ',' + parsed['County'])
        # print(geocode_result)
        if (len(geocode_result) != 0):
            parsed['Latitude'] = geocode_result[0]['geometry']['location']['lat']
            parsed['Longitude'] = geocode_result[0]['geometry']['location']['lng']
        else:
            skipped.append([lineNumber, parsed['Name']])
        print(parsed)
        lineNumber += 1

print(skipped)
