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
import multiprocessing

import settings

# import sys
# sys.path.insert(0, settings.caffe_root + 'python')
from skimage import io

"""
These are multiprocessed image handlers.  This inserts n number of images into a queue in a revolving fashion.
"""

class ImageFetcher:
    def __init__(self, q):
        self.q = q

    def __call__(self, im_params):
        url = im_params['url']
        try:
            image = get_image(im_params['url'])
            self.q.put({
                            'image': image,
                            'url': im_params['url'],
                            'name': im_params['name']
                       })
        except Exception:
            print("image fault from url: {url}".format(url=url))

def get_image(url):
    im = io.imread(url)
    return im
            

def start_image_process(urls, queue):
    number_cores = 4
    p = multiprocessing.Pool(number_cores)
    ifetcher = ImageFetcher(queue)
    while True:
        p.map(ifetcher, urls)
