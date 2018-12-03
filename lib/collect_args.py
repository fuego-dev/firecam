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

Simple utility to get args from command line or input

"""

import argparse
import logging

def collectArgs(requiredArgs, optionalArgs=[], parentParsers=None):
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR) # silence googleapiclient logs
    logging.basicConfig(format='%(asctime)s.%(msecs)03d: %(process)d: %(message)s', datefmt='%F %T')

    parser = argparse.ArgumentParser(parents=parentParsers if parentParsers != None else [])
    for arg in requiredArgs+optionalArgs:
        parser.add_argument('-'+arg[0], '--'+arg[1], help=arg[2], type=arg[3] if len(arg)>3 else None)
    args = parser.parse_args()

    vargs = vars(args)
    for arg in requiredArgs:
        if (vargs.get(arg[1]) == None):
            vargs[arg[1]] = input('Please enter the ' + arg[2] + ': ')

    logging.warning('Using these parameters')
    for arg in requiredArgs+optionalArgs:
        if vargs[arg[1]] != None:
            logging.warning(arg[2]+ ': ' + vargs[arg[1]])
    return args

def test():
    requiredArgs = [
        ["n", "name", "some string"],
        ["v", "value", "some integer", int],
    ]
    optionalArgs = [
        ["a", "alpha", "optional alpha"],
        ["b", "beta", "optional beta"],
    ]
    args = collectArgs(requiredArgs, optionalArgs=optionalArgs)
    print(args)

if __name__=="__main__":
    test()
