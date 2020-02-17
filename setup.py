#!/usr/bin/env python

from setuptools import setup

setup(name='firecam',
      version='1.0',
      # list folders, not files
      packages=['lib', 'train', 'tests', 'data_xform'],
      scripts=['get_image_hpwren.py',
               'data_xform/find_active_matches.py',
               'data_xform/camera_insert_sql.py',
               'data_xform/fire_coords.py',
               'data_xform/fire_date_parse.py',
               'data_xform/fire_insert_sql.py',
               'data_xform/image_insert_sql.py',
               'train/generate_test_set.py',
               'detection_policies/detect_always.py',
               'detection_policies/detect_never.py',
               ],
      package_data={'firecam': ['resources/output_labels.txt']}
      )
