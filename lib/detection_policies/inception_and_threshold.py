from gcp_helper import connect_to_prediction_service, predict_batch
import numpy as np
from scipy.ndimage.measurements import label
import os
import pathlib
from PIL import Image
import logging
import shutil
import goog_helper
import settings
import datetime
import math


class InceptionV3AndHistoricalThreshold:

    SEQUENCE_LENGTH = 1
    SEQUENCE_SPACING_MIN = None

    def __init__(self, settings, args, google_services, dbManager):
        self.dbManager = dbManager
        self.prediction_service = connect_to_prediction_service(settings.server_ip_and_port)
        self.args = args
        self.google_services = google_services

    def run_detection(self, image_spec):
        # This detection policy only uses a single image, so just take the last one
        last_image_spec = image_spec[-1]
        path = last_image_spec['path']
        timestamp = last_image_spec['timestamp']
        cameraID = last_image_spec['cameraID']

        #open image as numpy array
        img = np.asarray(Image.open(path))

        image_crops, segment_infos = self._segment_image(img)
        segments = self._classify(image_crops, segment_infos)
        if self.args.collectPositves:
            self._collect_positives(path, segments)
        detection_spec = self._record_and_filter(cameraID, timestamp, segments)

        return detection_spec

    def _record_and_filter(self, cameraID, timestamp, segments):
        """Record the scores for classified segments

        Args:
            cameraID (str): ID for camera associated with the image
            timestamp (int): time.time() value when image was taken
            segments (list): List of dictionary containing information on each segment
        """
        self._record_scores(cameraID, timestamp, segments)
        detection_spec = self._post_filter(cameraID, timestamp, segments)
        logging.warning('Highest score for camera %s: %f' % (cameraID, segments[0]['score']))
        return detection_spec

    def _collect_positives(self, origImgPath, segments):
        """Collect all positive scoring segments

        Copy the images for all segments that score highter than > .5 to google drive folder
        settings.positivePictures. These will be used to train future models.
        Also, copy the full image for reference.

        Args:
            origImgPath (str): path name for main image
            segments (list): List of dictionary containing information on each segment
        """
        positiveSegments = 0
        ppath = pathlib.PurePath(origImgPath)
        for segmentInfo in segments:
            if segmentInfo['score'] > .5:
                # do cropping now that we want to add to training set
                imgName = pathlib.PurePath(origImgPath).name
                outputDir = str(pathlib.PurePath(origImgPath).parent)
                imgNameNoExt = str(os.path.splitext(imgName)[0])
                coords = (segmentInfo['MinX'], segmentInfo['MinY'], segmentInfo['MaxX'], segmentInfo['MaxY'])
                # output cropped image
                cropImgName = imgNameNoExt + '_Crop_' + 'x'.join(list(map(lambda x: str(x), coords))) + '.jpg'
                cropImgPath = os.path.join(outputDir, cropImgName)
                origImg = Image.open(origImgPath)
                cropped_img = origImg.crop(coords)
                cropped_img.save(cropImgPath, format='JPEG')
                cropped_img.close()

                if hasattr(settings, 'positivePicturesDir'):
                    pp = pathlib.PurePath(cropImgPath)
                    destPath = os.path.join(settings.positivePicturesDir, pp.name)
                    shutil.copy(cropImgPath, destPath)
                else:
                    goog_helper.uploadFile(self.google_services, settings.positivePictures, cropImgPath)
                # delete the cropped file
                os.remove(cropImgPath)
                positiveSegments += 1

        if positiveSegments > 0:
            # Commenting out saving full images for now to reduce data
            # goog_helper.uploadFile(service, settings.positivePictures, imgPath)
            logging.warning('Found %d positives in image %s', positiveSegments, ppath.name)

    def _segment_image(self, image):
        """Segment the given image into sections to for smoke classificaiton

        Args:
            imgPath image: the image as a numpy array

        Returns:
            List of dictionary containing information on each segment
        """
        image_crops, segment_infos = self._cut_boxes_fixed(image)
        return image_crops, segment_infos

    def _classify(self, image_crops, segment_infos):
        """Classify each square

        Args:
            imgPath (str): filepath of the image to segment and clasify
            tfSession: Tensorflow session
            graph: Tensorflow graph
            labels: Tensorflow labels

        Returns:
            list of segments with scores sorted by decreasing score
        """
        batch = np.stack(image_crops)
        predictions = predict_batch(self.prediction_service, batch)

        # put predictions into expected form
        for idx, segmentInfo in enumerate(segment_infos):
            segmentInfo['score'] = float(predictions[idx, 1])

        segment_infos.sort(key=lambda x: -x['score'])
        return segment_infos

    def _record_scores(self, camera, timestamp, segments):
        """Record the smoke scores for each segment into SQL DB

        Args:
            camera (str): camera name
            timestamp (int):
            segments (list): List of dictionary containing information on each segment
        """
        dt = datetime.datetime.fromtimestamp(timestamp)
        secondsInDay = (dt.hour * 60 + dt.minute) * 60 + dt.second

        dbRows = []
        for segmentInfo in segments:
            dbRow = {
                'CameraName': camera,
                'Timestamp': timestamp,
                'MinX': segmentInfo['MinX'],
                'MinY': segmentInfo['MinY'],
                'MaxX': segmentInfo['MaxX'],
                'MaxY': segmentInfo['MaxY'],
                'Score': segmentInfo['score'],
                'SecondsInDay': secondsInDay
            }
            dbRows.append(dbRow)
        self.dbManager.add_data('scores', dbRows)

    def _post_filter(self, camera, timestamp, segments):
        """Post classification filter to reduce false positives

        Many times smoke classification scores segments with haze and glare
        above 0.5.  Haze and glare occur tend to occur at similar time over
        multiple days, so this filter raises the threshold based on the max
        smoke score for same segment at same time of day over the last few days.
        Score must be > halfway between max value and 1.  Also, minimum .1 above max.

        Args:
            camera (str): camera name
            timestamp (int):
            segments (list): Sorted List of dictionary containing information on each segment

        Returns:
            DetectionSpec
        """
        # enable the next few lines fakes a detection to test alerting functionality
        # maxFireSegment = segments[0]
        # maxFireSegment['HistAvg'] = 0.1
        # maxFireSegment['HistMax'] = 0.2
        # maxFireSegment['HistNumSamples'] = 10
        # return maxFireSegment

        # segments is sorted, so skip all work if max score is < .5
        if segments[0]['score'] < .5:
            return []

        sqlTemplate = """SELECT MinX,MinY,MaxX,MaxY,count(*) as cnt, avg(score) as avgs, max(score) as maxs FROM scores
        WHERE CameraName='%s' and Timestamp > %s and Timestamp < %s and SecondsInDay > %s and SecondsInDay < %s
        GROUP BY MinX,MinY,MaxX,MaxY"""

        dt = datetime.datetime.fromtimestamp(timestamp)
        secondsInDay = (dt.hour * 60 + dt.minute) * 60 + dt.second
        sqlStr = sqlTemplate % (
        camera, timestamp - 60 * 60 * int(24 * 3.5), timestamp - 60 * 60 * 12, secondsInDay - 60 * 60,
        secondsInDay + 60 * 60)
        # print('sql', sqlStr, timestamp)
        dbResult = self.dbManager.query(sqlStr)
        #for debugging
        # dbResult = self.dbManager.query(
        #     """SELECT MinX,MinY,MaxX,MaxY,count(*), avg(score) as avgs, max(score) as maxs FROM scores
        #     WHERE CameraName='{}' and Timestamp > {}   GROUP BY MinX,MinY,MaxX,MaxY""".format(
        #         camera, timestamp - 60 * 60 * int(24 * 3.5)) )

        # if len(dbResult) > 0:
        #     print('post filter result', dbResult)
        maxFireSegment = None
        maxFireScore = 0
        positive_detection_indices = []
        for index, segmentInfo in enumerate(segments):
            if segmentInfo['score'] < .5:  # segments is sorted. we've reached end of segments >= .5
                break
            for row in dbResult:
                if (row['minx'] == segmentInfo['MinX'] and row['miny'] == segmentInfo['MinY'] and
                        row['maxx'] == segmentInfo['MaxX'] and row['maxy'] == segmentInfo['MaxY']):
                    threshold = (row['maxs'] + 1) / 2  # threshold is halfway between max and 1
                    # Segments with historical value above 0.8 are too noisy, so discard them by setting
                    # threshold at least .2 above max.  Also requires .7 to reach .9 vs just .85
                    threshold = max(threshold, row['maxs'] + 0.2)
                    # print('thresh', row['minx'], row['miny'], row['maxx'], row['maxy'], row['maxs'], threshold)
                    if (segmentInfo['score'] > threshold) and (segmentInfo['score'] > maxFireScore):
                        positive_detection_indices.append(index)

            # positive_detection_indices.append(index)

        ### Do conversion into DetectionSpec (i.e. merge segments into contiguous bounding boxes when they are adjacent
        #convert to rows and cols
        x_centers = sorted(list(set([(entry['MinX'] + entry['MaxX']) / 2 for entry in segments])))
        y_centers = sorted(list(set([(entry['MinY'] + entry['MaxY']) /2 for entry in segments])))
        row_col = np.array([[y_centers.index((entry['MinY'] + entry['MaxY']) / 2),
                x_centers.index((entry['MinX'] + entry['MaxX']) / 2) ] for entry in segments])
        #identify contiguous regions of positive detections to draw boundign boxes
        positive_row_cols = row_col[positive_detection_indices]
        segment_image = np.zeros((len(y_centers), len(x_centers)), np.int)
        segment_image[positive_row_cols[:, 0], positive_row_cols[:, 1]] = 1
        labelled_image, num_rois = label(segment_image, np.ones((3, 3), dtype=np.int))
        detection_spec = []
        for roi_index in np.arange(1, num_rois + 1):
            #find min and max spatial coordinates of contiguous region, and take max softmax score over this region
            row_indices, col_indices = np.where(labelled_image == roi_index)
            max_score = 0.0
            for entry in segments:
                center_x = (entry['MinX'] + entry['MaxX']) / 2
                center_y = (entry['MinY'] + entry['MaxY']) / 2
                col_index = x_centers.index(center_x)
                row_index = y_centers.index(center_y)
                if np.any(np.logical_and(row_index == positive_row_cols[:, 0], col_index == positive_row_cols[:, 1])):
                    max_score = np.maximum(max_score, entry['score'])
                if x_centers[np.min(col_indices)] == center_x:
                    min_x = entry['MinX']
                if x_centers[np.max(col_indices)] == center_x:
                    max_x = entry['MaxX']
                if y_centers[np.min(row_indices)] == center_y:
                    min_y = entry['MinY']
                if y_centers[np.max(row_indices)] == center_y:
                    max_y = entry['MaxY']
            detection_spec.append({'y': min_y, 'x': min_x, 'width': max_x - min_x, 'height': max_y - min_y, 'score': max_score})

        return detection_spec

    def _cut_boxes_fixed(self, image):
        """Cut the given image into fixed size boxes

        Divide the given image into square segments of 299x299 (segmentSize below)
        to match the size of images used by InceptionV3 image classification
        machine learning model.  This function uses the getSegmentRanges() function
        above to calculate the exact start and end of each square

        Args:
            imgOrig (Image): Image object of the original image
            outputDirectory (str): name of directory to store the segments
            imageFileName (str): nane of image file (used as segment file prefix)
            callBackFn (function): callback function that's called for each square

        Returns:
            (list): list of segments with numpy arrays of image patches and coordinates
        """
        segmentSize = 299
        segments = []
        xRanges = self._get_segment_ranges(image.shape[1], segmentSize)
        yRanges = self._get_segment_ranges(image.shape[0], segmentSize)

        crops = []
        for yRange in yRanges:
            for xRange in xRanges:
                crops.append(image[yRange[0]:yRange[1], xRange[0]:xRange[1]])
                coords = (xRange[0], yRange[0], xRange[1], yRange[1])
                segments.append({
                    'MinX': coords[0],
                    'MinY': coords[1],
                    'MaxX': coords[2],
                    'MaxY': coords[3]
                })
        return crops, segments

    def _get_segment_ranges(self, fullSize, segmentSize):
        """Break the given fullSize into ranges of segmentSize

        Divide the range (0,fullSize) into multiple ranges of size
        segmentSize that are equally spaced apart and have approximately
        10% overlap (overlapRatio)

        Args:
            fullSize (int): size of the full range (0, fullSize)
            segmentSize (int): size of each segment

        Returns:
            (list): list of tuples (start, end) marking each segment's range
        """
        overlapRatio = 1.1
        if fullSize <= segmentSize:
            return [(0, fullSize)]
        firstCenter = int(segmentSize / 2)
        lastCenter = fullSize - int(segmentSize / 2)
        assert lastCenter > firstCenter
        flexSize = lastCenter - firstCenter
        numSegments = math.ceil(flexSize / (segmentSize / overlapRatio))
        offset = flexSize / numSegments
        ranges = []
        for i in range(numSegments):
            center = firstCenter + round(i * offset)
            start = center - int(segmentSize / 2)
            end = min(start + segmentSize, fullSize)
            ranges.append((start, end))
        ranges.append((fullSize - segmentSize, fullSize))
        # print('ranges', fullSize, segmentSize, ranges)
        # lastC = 0
        # for i, r in enumerate(ranges):
        #     c = (r[0] + r[1])/2
        #     print(i, r[0], r[1], c, c - lastC)
        #     lastC = c
        return ranges

