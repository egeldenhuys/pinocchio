from typing import Dict, List, IO
from io import IOBase
import csv
import io


class CsvStatus(object):
    """Holds information on the validity of the csv file and the returned data"""

    def __init__(self, valid: bool, error_message: str = None, data: List[Dict[str, str]] = None) -> None:
        """
        :param valid: Is the CSV file valid
        :param error_message: A descriptive message of where and why the error occured
        :param data: If valid, the data that was read from the csv file
        """
        self.valid: bool = valid
        self.error_message: str = error_message
        self.data = data


def validate_header(csv_file, fields: List[str]) -> CsvStatus:
    """Check if the given fields appear in the csv header

    :param csv_file: The already open file to read
    :param fields: The list of header columns to search for
    :rtype: CsvStatus

    .. note:: Resets the seek location in the file
    """
    csv_file.seek(0)
    reader = csv.reader(csv_file, fields, skipinitialspace=True)
    header: List[str] = next(reader)

    for item in fields:
        if item not in header:
            csv_file.seek(0)
            return CsvStatus(valid=False, error_message="Field " + item + " was not found in the header")

    csv_file.seek(0)
    return CsvStatus(valid=True, error_message=None)


def validate_csv(fields: List[str], file_path: str) -> CsvStatus:
    with open(file_path) as csv_file:
        header_result = validate_header(csv_file, fields)

        if not header_result.valid:
            return header_result

        header_reader = csv.reader(csv_file, skipinitialspace=True)
        header = next(header_reader)

        csv_file.seek(0)

        reader: csv.DictReader = csv.DictReader(csv_file, skipinitialspace=True)

        # Try parsing csv into tuples according to the given fields
        users: List[Dict[str, str]] = list()

        for row in reader:
            # Make sure all fields were found in the row
            for key, value in row.items():
                if not value:
                    return CsvStatus(valid=False, error_message='No value found for key \'' + key + '\' on line ' + str(reader.line_num))
            users.append(row)

    if users:
        return CsvStatus(valid=True, error_message='', data=users)
    else:
        return CsvStatus(valid=False, error_message='')
