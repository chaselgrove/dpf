# See file COPYING distributed with dpf for copyright and license.

import csv
import json

class DataHandler:

    """base class for type handlers"""

class JSONHandler(DataHandler):

    from_type = 'text/json'
    to_types = ['text/json']

    def validate(self, fname):
        data = open(fname).read()
        try:
            json.loads(data)
        except ValueError:
            return False
        return True

class CSVHandler(DataHandler):

    from_type = 'text/csv'
    to_types = ['text/json']

    def validate(self, fname):
        try:
            with open(fname) as fo:
                reader = csv.reader(fo)
                for row in reader:
                    pass
        except csv.Error:
            return False
        return True

    def convert(self, fname, content_type):
        with open(fname) as fo:
            reader = csv.reader(fo)
            l = [ row for row in reader ]
        return json.dumps(l)

# eof
