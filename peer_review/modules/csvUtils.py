from typing import Dict, List
import csv


class CsvStatus(object):
    """Holds information on the validity of the csv file and the returned data"""

    def __init__(self, valid: bool, error_message: str, data: List[Dict[str, str]] = None) -> None:
        self.valid: bool = valid
        self.error_message: str = error_message
        self.data = data


def validate_csv(fields: List[str], file_path: str) -> CsvStatus:
    with open(file_path) as csv_file:
        reader = csv.reader(csv_file, skipinitialspace=True)
        header: List[str] = next(reader)

        # Validate header
        for item in fields:
            if item not in header:
                return CsvStatus(valid=False, error_message="Field " + item + " was not found in the header")

        # Try parsing csv into tuples according to the given fields
        users: List[Dict[str, str]] = list()

        for row in reader:
            user: Dict[str, str] = dict()

            for i in range(0, len(header)):
                user[header[i]] = row[i]

            users.append(user)

    if users:
        return CsvStatus(valid=True, error_message='', data=users)
    else:
        return CsvStatus(valid=False, error_message='')
