# Cropper Settings
import logging
from pathlib import Path


class Settings(user='cropper', test_mode=True):
    """
    Settings will create some local folders.
    And set some other variables.
    """

    # silence googleapiclient logs
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    # silence the PILLOW logs
    logging.getLogger('PIL.Image').setLevel(logging.ERROR)

    local_log_level = logging.DEBUG
    # initialize local logs
    logging.basicConfig(level=local_log_level,
                        format='%(asctime)s.%(msecs)03d: %(process)d: %(message)s',
                        datefmt='%F %T')
    logger = logging.getLogger(__file__)

    p = Path()
    fuegoRoot = p.resolve()
    logger.debug(f'fuegoRoot: {fuegoRoot}, is_dir: {fuegoRoot.is_dir()}')

    googleTokenFile = fuegoRoot / "token.json"
    googleCredsFile = fuegoRoot / "credentials.json"
    assert googleCredsFile.is_file()

    localCropDir = fuegoRoot / "cropped"
    # make the directory if it doesn't already exist
    Path(localCropDir).mkdir(exist_ok=True, parents=True)

    downloadDir = fuegoRoot / "orig"
    # make the directory if it doesn't already exist
    Path(downloadDir).mkdir(exist_ok=True, parents=True)

    # archive_storage_bucket = "fuego-firecam-a"
    #
    # teamDriveID = '0ADX9uPkOmsDJUk9PVA'  # Fuego Smoke
    # allPictures = '1SCXFLE25EbQUQMvTcWfeHFU29qxN8WMM'  # Pictures  - Samples and Full Sets

    if test_mode:
        imagesSheet = '1YC-LBaL1cbqgQ0chkAkt6Ll74WoEk3kke1L7zVXPcUw'
        cropImagesSheet = '1aLX8lug2uQIewUCLzmZUe0ZNjZ6ODPvkQo1WJPlVRNQ'
        smokePictures = '1qGCYrCDhihFgVSwkvD6Gl7WzG4QeNNxL'  # test-smoke
        # cropSmokePictures = '15mtvAWTtFV8if1y-isKFDKlxUdlB4Wfm'  # test-crop-smoke
        # nonSmokePictures = '1PolO0-LCSST8bgjtEBHxCQM8Nl_X-O9_'  # test-other
        # motionPictures = '1etxLJp-J6R4uXET2MhdPIIdQdlyCOVjf'  # test-motion

    else:
        imagesSheet = '19dd0I8XiLbWmzFPzDdXFXkTPoeuHtjZ1r3aaXnzsB-g'  # Images
        cropImagesSheet = '12OH_cqLomFXd3JVoXCcnNmr8xHSuF6mmo-i_gEYA2gc'  # Cropped Images
        smokePictures = '1jq9p2A5BVLh1oWKktpV1oaWTVUU9KmNJ'  # Smoke
        cropSmokePictures = '1e-mn0H55j2qJHgp0uYNXpNel0RHOvxcE'  # Cropped Smoke
        nonSmokePictures = '14UoqUfXupfOmkCmm8MEyYP3xvPLjXnh0'  # Full Set (Other)
        motionPictures = '10okQ8-xNOsgy5wghNnVdaZKALi6huQYX'  # Full Set (Motion Testing)

    # imagesSheetAppendRange = 'A1'  # append below this cell
    # cropImagesSheetAppendRange = 'A1'  # append below this cell
    # cropEveryNMinutes = 1  # crop smoke images that are at least 1 minutes apart
    # camerasSheet = '1wG5j2p5LfgZc7dluKC6g8eGSg_B1KLZ9K147X5WYYhQ'  # Camera Names and Codenames
    # camerasSheetRange = 'Code Name Archive Mapping!A1:G1000'
    #
    # alertwildfirekey = 'ffd61ee247194f80aa2a7859d15db04a'

    # IMG_CLASSES = {
    #     'smoke': smokePictures,
    #     'nonSmoke': nonSmokePictures,
    #     'motion': motionPictures,
    #     'cropSmoke': cropSmokePictures
    # }
