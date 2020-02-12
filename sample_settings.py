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
fuegoRoot = 'XXX/firecam'
googleTokenFile = 'XXX/token.json'
googleCredsFile = 'XXX/credentials.json'
#localCropDir = 'XXX/cropped' #local system directory with cropped images
model_file = 'XXX/output_graph.pb'
labels_file = 'XXX/output_labels.txt'
db_file = 'XXX/local.db'
tfSlimDir = 'XXX/tf_models/research/slim'
downloadDir = 'XXX/orig'
archive_storage_bucket = "fuego-firecam-a"

detectionPolicy = 'inception_and_threshold' #  'always', 'never'

teamDriveID = '0ADX9uPkOmsDJUk9PVA' # Fuego Smoke
allPictures = '1SCXFLE25EbQUQMvTcWfeHFU29qxN8WMM' # Pictures  - Samples and Full Sets
# smokePictures = '1jq9p2A5BVLh1oWKktpV1oaWTVUU9KmNJ' # Smoke
# nonSmokePictures = '14UoqUfXupfOmkCmm8MEyYP3xvPLjXnh0' # Full Set (Other)
# motionPictures = '10okQ8-xNOsgy5wghNnVdaZKALi6huQYX' # Full Set (Motion Testing)
# cropSmokePictures = '1e-mn0H55j2qJHgp0uYNXpNel0RHOvxcE' # Cropped Smoke
# detectionPictures = '1GG-5_FzCdXagqU9sVGf3fyc9oBq7wSqy' # Detections
smokePictures = '1qGCYrCDhihFgVSwkvD6Gl7WzG4QeNNxL' # test-smoke
nonSmokePictures = '1PolO0-LCSST8bgjtEBHxCQM8Nl_X-O9_' # test-other
motionPictures = '1etxLJp-J6R4uXET2MhdPIIdQdlyCOVjf' # test-motion
cropSmokePictures = '15mtvAWTtFV8if1y-isKFDKlxUdlB4Wfm' # test-crop-smoke
detectionPictures = '1cNe2ohmCAJwgFPh5_nT4zaTwlHRtMRw6' # test-detections
positivePictures = '154ayDGQ-cc89eGbbj48byTe1K4Lvnwan' # test-positives

imagesSheet = '19dd0I8XiLbWmzFPzDdXFXkTPoeuHtjZ1r3aaXnzsB-g' # Images
imagesSheetAppendRange = 'A1' # append below this cell
cropImagesSheet = '12OH_cqLomFXd3JVoXCcnNmr8xHSuF6mmo-i_gEYA2gc' # Cropped Images
cropImagesSheetAppendRange = 'A1' # append below this cell
cropEveryNMinutes = 1 # crop smoke images that are at least 1 minutes apart
camerasSheet = '1wG5j2p5LfgZc7dluKC6g8eGSg_B1KLZ9K147X5WYYhQ' # Camera Names and Codenames
camerasSheetRange = 'Code Name Archive Mapping!A1:G1000'

fuegoEmail = 'fuego.response@gmail.com'
fuegoPasswd = 'do not put real password in files in open source git repo'

forest_service_url = 'do not put real url in files in open source git repo'
forest_service_key = 'do not put real key in files in open source git repo'


psqlHost = '127.0.0.1'
psqlDb = 'postgres'
psqlUser = 'postgres'
psqlPasswd = 'postgres'

IMG_CLASSES = {
    'smoke': smokePictures,
    'nonSmoke': nonSmokePictures,
    'motion': motionPictures,
    'cropSmoke': cropSmokePictures
}

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR) # silence googleapiclient logs
logging.basicConfig(format='%(asctime)s.%(msecs)03d: %(process)d: %(message)s', datefmt='%F %T')
