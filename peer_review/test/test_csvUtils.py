from django.test import TestCase
import peer_review.modules.csvUtils as csv_utils
import os

from typing import Dict


class CsvUtilsTest(TestCase):
    """Tests relating to the csvUtils module

    Does not test error_message

    .. todo:: Remove inconsistent style from test csv files. Isolate styles
    to one test
    """

    def setUp(self):
        module_dir = os.path.dirname(__file__)
        self.csv_dir: str = module_dir + "/test_csvUtils"
        self.fields: list = ['title',
                             'initials',
                             'name',
                             'surname',
                             'cell',
                             'email',
                             'user_id']

    def test_header_validation(self):
        # Pass when all fields are also in the csv header
        # Pass when there are spaces after the ',' delimiter
        result: csv_utils.CsvStatus = csv_utils.validate_csv(self.fields,
                                                             self.csv_dir +
                                                             '/valid.csv')
        self.assertEqual(result.valid, True,
                         "Could not find all the fields in csv header")

        # Fail when field not found in csv header
        result = csv_utils.validate_csv(self.fields,
                                        self.csv_dir + '/invalid_header.csv')
        self.assertEqual(result.valid, False)

        # Pass when there are extra fields in the csv header
        result = csv_utils.validate_csv(self.fields,
                                        self.csv_dir +
                                        '/valid_header_extra.csv')
        self.assertEqual(result.valid, True)

    def test_user_validation(self):
        result: csv_utils.CsvStatus = csv_utils.validate_csv(self.fields,
                                                             self.csv_dir +
                                                             '/valid_users.csv')
        self.assertEqual(result.valid, True)
        self.assertNotEqual(result.data, None)
        self.assertEqual(len(result.data), 3);

        user1: Dict[str, str] = dict()
        user1['title'] = 'Mrs'
        user1['initials'] = 'T'
        user1['name'] = 'Tina'
        user1['surname'] = 'Smith'
        user1['email'] = 'Tsmith@example.com'
        user1['cell'] = '323424'
        user1['user_id'] = 'u478955545'

        user2: Dict[str, str] = dict()
        user2['title'] = 'Mr'
        user2['initials'] = 'J'
        user2['name'] = 'John'
        user2['surname'] = 'Doe'
        user2['email'] = 'john.doe@example.com'
        user2['cell'] = '838374742'
        user2['user_id'] = 'johny'

        user3: Dict[str, str] = dict()
        user3['title'] = 'Mr'
        user3['initials'] = 'F'
        user3['name'] = 'Fred'
        user3['surname'] = 'Smith'
        user3['email'] = 'fred.smith@example.com'
        user3['cell'] = '333343'
        user3['user_id'] = 'TheFred'

        # Pass when users are returned in order according to the structure
        # List[Dict[str, str]]
        self.assertDictEqual(result.data[0], user2)
        self.assertDictEqual(result.data[1], user3)
        self.assertDictEqual(result.data[2], user1)

    def test_no_users(self):
        result: csv_utils.CsvStatus = csv_utils.validate_csv(self.fields,
                                                             self.csv_dir +
                                                             '/no_users.csv')
        self.assertEqual(result.valid, False)
        self.assertEqual(result.data, None)

    def test_invalid_row(self):
        result: csv_utils.CsvStatus = csv_utils.validate_csv(self.fields,
                                                             self.csv_dir +
                                                             '/invalid_row.csv')
        self.assertEqual(result.valid, False)
        self.assertEqual(result.data, None)

        result = csv_utils.validate_csv(self.fields,
                                        self.csv_dir + '/invalid_row2.csv')
        self.assertEqual(result.valid, False)
        self.assertEqual(result.data, None)

    def test_styles(self):
        result: csv_utils.CsvStatus = csv_utils.validate_csv(self.fields,
                                                             self.csv_dir +
                                                             '/valid_style.csv')
        self.assertEqual(result.valid, True)

        user2: Dict[str, str] = dict()
        user2['title'] = 'Mr'
        user2['initials'] = 'J'
        user2['name'] = 'John Fred James'
        user2['surname'] = 'Doe'
        user2['email'] = 'john.doe@example.com'
        user2['cell'] = '838374742'
        user2['user_id'] = 'johny'

        self.assertDictEqual(result.data[0], user2)
