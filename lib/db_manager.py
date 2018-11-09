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
This file is in charge of managing database pass through. The database 
contains information such as urls for the different image sources 
we may be pulling from as well as information of past detected events.

It can be used to read from the db by the image handler or to write to
the database by tools we use to populate it.

It runs on sqllite3

"""

import sqlite3
import datetime

def _dict_factory(cursor, row):
    """
    This is a helper function to create a dictionary using the column names
    from the database as the keys

    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d



class DbManager(object):
    def __init__(self, dbname='resources/local.db'):
        self.conn = sqlite3.connect(dbname)
        self.conn.row_factory = _dict_factory

        sources_schema = [
            ('name', 'TEXT'),
            ('url', 'TEXT'),
            ('last_date', 'TEXT')
        ]

        fires_schema = [
            ('Name', 'TEXT'),
            ('Url', 'TEXT'),
            ('Year', 'INT'),
            ('County', 'TEXT'),
            ('Location', 'TEXT'),
            ('Acres', 'TEXT'),
            ('EvacInfo', 'TEXT'),
            ('AdminUnit', 'TEXT'),
            ('Started', 'TEXT'),
            ('Updated', 'TEXT'),
            ('Latitude', 'REAL'),
            ('Longitude', 'REAL')
        ]

        cameras_schema = [
            ('Name', 'TEXT'),
            ('Latitude', 'REAL'),
            ('Longitude', 'REAL')
        ]
        
        images_schema = [
            ('ImageID', 'TEXT'),
            ('ImageClass', 'TEXT'),
            ('FireName', 'TEXT'),
            ('CameraName', 'TEXT'),
            ('Timestamp', 'INT'),
            ('Smoke', 'TEXT'),
            ('Fog', 'TEXT'),
            ('Rain', 'TEXT'),
            ('Glare', 'TEXT'),
            ('Snow', 'TEXT'),
        ]

        cropped_schema = [
            ('CroppedID', 'TEXT'),
            ('MinX', 'INT'),
            ('MinY', 'INT'),
            ('MaxX', 'INT'),
            ('MaxY', 'INT'),
            ('EntireImageID', 'TEXT'),
        ]

        scores_schema = [
            ('CameraName', 'TEXT'),
            ('Timestamp', 'INT'),
            ('MinX', 'INT'),
            ('MinY', 'INT'),
            ('MaxX', 'INT'),
            ('MaxY', 'INT'),
            ('Score', 'REAL'),
        ]

        alerts_schema = [
            ('CameraName', 'TEXT'),
            ('Timestamp', 'INT'),
            ('ImageID', 'TEXT'),
        ]

        self.tables = {
            'sources': sources_schema,
            'fires': fires_schema,
            'cameras': cameras_schema,
            'images': images_schema,
            'cropped': cropped_schema,
            'scores': scores_schema,
            'alerts': alerts_schema,
        }

        self.sources_table_name = 'sources'
        self._check_local_db()


    def __del__(self):
        self.conn.close()

    def get_sources(self):
        sources = []
        self.conn.row_factory = _dict_factory
        c = self.conn.cursor()
        for row in c.execute("SELECT * FROM %s order by name" % self.sources_table_name):
            sources.append(row)
        return sources

    def create_db(self):
        pass

    def add_url(self, url, urlname):
        date = datetime.datetime.utcnow().isoformat()
        self.add_data('sources', {'name': urlname, 'url': url, 'last_date': date})

    def add_data(self, tableName, keyValues, commit=True):
        sql_template = 'insert into {table_name} ({fields}) values ({values})'
        db_command = sql_template.format(
            table_name = tableName,
            fields = ", ".join(key for (key, _) in keyValues.items()),
            values = ", ".join(repr(val) for (_, val) in keyValues.items())
        )
        self.conn.execute(db_command)
        if commit:
            self.conn.commit()


    def commit(self):
        self.conn.commit()


    def query(self, queryStr):
        result = []
        c = self.conn.cursor()
        for row in c.execute(queryStr):
            result.append(row)
        return result


    def _check_local_db(self):
        """
        This ensures that the database exists and that the specified
        table exists within it.

        """
        sql_create_template = 'create table if not exists {table_name} ({fields})'
        c = self.conn.cursor()
        for tableName, tableSchema in self.tables.items():
            db_command = sql_create_template.format(
                table_name = tableName,
                fields = ", ".join(
                    variable + " " + data_type
                    for (variable, data_type) in tableSchema
                )
            )
            c.execute(db_command)
        self.conn.commit()