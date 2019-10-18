#url
#requests
#parse.
#save?/upload to a google folder
#write continual check program




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


import os
import sys
fuegoRoot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(fuegoRoot, 'lib'))
sys.path.insert(0, fuegoRoot)
import settings
settings.fuegoRoot = fuegoRoot 
import requests
import goog_helper
import collect_args
import dateutil
import csv
import logging
import time
import urllib.parse as urlp


if settings.forest_service_url == 'do not put real url in files in open source git repo':
    logging.warning('Please update settings.forest_service_url with the url provided to you')
baseApiUrl = urlp.urlparse(settings.forest_service_url)#initialize
if settings.forest_service_key == 'do not put real key in files in open source git repo':
    logging.warning('Please update settings.forest_service_key with the key provided to you')



def getApiUrl(endpoint, queryParams = None):
    """builds the url of a forestry request
    Args:
        endpoint (str): name of service to look at
        (opt) queryParams (str): optional parameters to add to url
    Returns:
        url (str): built url for alertwildfire services
        
    """
    if queryParams:
        urlParts = baseApiUrl._replace(path = baseApiUrl.path+endpoint, query = queryParams)
    else:
        urlParts = baseApiUrl._replace(path = baseApiUrl.path+endpoint)
    url = urlp.urlunparse(urlParts)
    return url

def invokeApi(endpoint, queryParams = None, stream = False, url_override = False):
    """invokes a request of the forestry system
    Args:
        endpoint (str): name of service to look at
        (opt) queryParams (str): optional parameters to add to url
        (opt) stream (bool): should the request be streamed
        (opt) url_override (str): forceful override of url to be used
    Returns:
        response (request): the request response from alert wildfire
        
    """
    headers = {'X-Api-Key': settings.forest_service_key}
    if url_override:
        url = url_override
    else:
        url = getApiUrl(endpoint, queryParams )
    response = requests.get(url, headers = headers, stream = stream)
    return response

def get_forestryDB(timefrom = None, timeto = None ):
    """organizes DB query input and output
    Args:
        timefrom (str): the start time in the format 'YYYY-MM-DDThh:mm:ss'
        timeto   (str): the start time in the format 'YYYY-MM-DDThh:mm:ss'
    Returns:
        features in DB or NONE
    """
    Params = "from="+timefrom+"&to="+timeto
    response = invokeApi("", queryParams = Params, stream = False)
    if response.status_code == 404:
        return 

    return response.json()['features']

def unpack_forestryDB(objects):
    """unpacks hierarchical structure of Forestry DB objects into a easily savable format
    Args:
        objects (dict): Forestry DB nested dict object
    Returns:
        values  (list): list of values saved in dict object
    """
    values = [
    objects['properties']['ig_test'],
    objects['properties']['ig_date'],
    objects['properties']['created'],
    objects['properties']['id'],
    objects['properties']['ig_time'],
    objects['properties']['ig_confidence'],
    objects['properties']['ig_identity'],
    objects['geometry']['coordinates'][0],
    objects['geometry']['coordinates'][1],
    objects['geometry']['type'],
    objects['type']
    ]
    return values




def main():
    """records the Forestry fire database
    Args:
        -c continual monitoring: continually monitor the forestry system
        -s start time override:  override the start time
        -e end time override:    override the end time
    Returns:
        None
    """
    reqArgs = []
    optArgs = [
        ["c", "continual_monitoring", "continually monitor the forestry system"],
        ["s", "start_time_override", "override the start time"],
        ["e", "end_time_override", "override the end time"]
    ]
    args = collect_args.collectArgs(reqArgs,  optionalArgs=optArgs, parentParsers=[goog_helper.getParentParser()])
    googleServices = goog_helper.getGoogleServices(settings, args)
    if args.start_time_override and  args.end_time_override:
        startTimeDT = args.start_time_override
        endTimeDT = args.end_time_override
    if args.start_time_override and not args.end_time_override:
        logging.warning("Please provide a start (-s) and end (-e) time in the format of 'YYYY-MM-DDThh:mm:ss' to your search")
        return 

    if args.continual_monitoring:
        csvFile = open('forestryDB_continual.csv', 'w')
        writer = csv.writer(csvFile)
        header1 = ["properties","","","","","","","geometry","","","type"]
        header2 = ["ig_test","ig_date","created","id","ig_time","ig_confidence","ig_identity","coordinates","","type"]
        writer.writerow(header1)
        writer.writerow(header2)
        csvFile.close()
        while True:
            csvFile = open('forestryDB_continual.csv', 'a')
            writer = csv.writer(csvFile)
            startTimeDT = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()-10*60))
            endTimeDT = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))       
            data = get_forestryDB(timefrom = startTimeDT, timeto = endTimeDT)
            tic = time.time()
            logging.warning('found %s fires',len(data))
            for elem in data:
                #upload_data 
                values = unpack_forestryDB(elem)
                writer.writerow(values)
            csvFile.close()
            time.sleep(10*60-(time.time()-tic))
    else:
        data = get_forestryDB(timefrom = startTimeDT, timeto = endTimeDT)
        if data == None:
            logging.warning("request could not be made")
            return 
        file_name = 'forestryDBfrom'+startTimeDT+'to'+endTimeDT+'.csv'
        csvFile = open(file_name.replace(":",";").replace(" ","T"), 'w')
        writer = csv.writer(csvFile)
        header1 = ["properties","","","","","","","geometry","","","type"]
        header2 = ["ig_test","ig_date","created","id","ig_time","ig_confidence","ig_identity","coordinates","","type"]
        writer.writerow(header1)
        writer.writerow(header2)
        for elem in data:
            #upload_data 
            values = unpack_forestryDB(elem)
            writer.writerow(values)

        csvFile.close()


if __name__=="__main__":
    main()

    
