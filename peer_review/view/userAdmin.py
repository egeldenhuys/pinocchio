"""Functions for uploading User CSV files"""

import os
from typing import List, Dict, Any
import ntpath
from django.http import HttpResponse
from django.shortcuts import render
from peer_review.decorators.adminRequired import admin_required
from peer_review.forms import DocumentForm, UserForm
from peer_review.models import User, Document
from peer_review.view.userManagement import create_user_send_otp
from peer_review.modules.csv_utils import CsvStatus
import peer_review.modules.csv_utils as csv_utils

# TODO(egeldenhuys): Rename this module to relate to user CSV upload
# TODO(egeldenhuys): Test the functions in this module


def create_user(user: Dict[str, str]) -> bool:
    """Create a new user in the database and send a OTP email

    Args:
        user: The user to create

    Returns:
        True if the user was successfully created, otherwise False
    """
    django_user = create_user_send_otp(
        user_user_id=user['user_id'],
        user_status='U',
        user_title=user['title'],
        user_initials=user['initials'],
        user_name=user['name'],
        user_surname=user['surname'],
        user_cell=user['cell'],
        user_email=user['email'])

    return bool(django_user)


@admin_required
def confirm_csv(request) -> HttpResponse:
    """Add the users in the given CSV file

    Note:
        Expects files to be in ./media/documents

    Context Args:
        request_id (str): The path of the CSV file on the server
        confirm (int):
            0: Cancel operation
            1: Add users

    Context Returns:
        message (str): Message indicating success or failure
        error_code (int):
            0 - No error
            1 - Some error
    """
    # TODO(egeldenhuys): Get fields from User Model
    fields: list = [
        'title', 'initials', 'name', 'surname', 'cell', 'email', 'user_id'
    ]

    base_dir: str = 'media/documents'

    context_data: Dict[str, Any] = init_context_data()

    if request.method == 'POST':
        print(request.POST)
        if 'request_id' in request.POST and 'confirm' in request.POST:
            request_id: str = str(request.POST['request_id'])
            confirm: int = int(request.POST['confirm'])
            file_path = os.path.join(base_dir, request_id)
            if confirm == 1:
                status: CsvStatus = csv_utils.validate_csv(fields, file_path)

                if status.valid:
                    if not users_exist(status.data):
                        for user in status.data:
                            if not create_user(user):
                                context_data['error_code'] = 1
                                context_data[
                                    'message'] = 'Error creating the user with user_id %s' % user[
                                        'user_id']
                                break
                        # Success
                        context_data['error_code'] = 0
                        context_data[
                            'message'] = 'All users were succesfully created'
                    else:
                        context_data['error_code'] = 1
                        context_data[
                            'message'] = 'A user in the csv already exists in the database. \
                            Please retry for more information.'
                else:
                    context_data['error_code'] = 1
                    context_data[
                        'message'] = 'Yer a wizard! The csv file on the server has been corrupted.'
            else:
                context_data['error_code'] = 0
                context_data['message'] = 'Operation has been cancelled'

            if os.path.isfile(file_path):
                os.remove(file_path)

        else:
            context_data['error_code'] = 1
            context_data['message'] = 'Invalid or no parameters sent'

    return render(request, 'peer_review/userAdmin.html', context_data)


def init_context_data() -> Dict[str, Any]:
    """Return context data required for the page to function"""
    context_data: Dict[str, Any] = dict()

    context_data['users'] = User.objects.all
    context_data['user_form'] = UserForm()

    context_data['csv_upload_args']: Dict[str, Any] = dict()
    context_data['csv_upload_args']['doc_form'] = DocumentForm()

    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir)

    with open(file_path + '/../text/otp_email.txt', 'r+') as file:
        context_data['email_text'] = file.read()

    return context_data


def path_leaf(path: str) -> str:
    """Get the file name from the path

    Source:
        https://stackoverflow.com/a/8384788

    Args:
        path: The full path of the file

    Returns:
        The file name
    """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def users_exist(user_list: List[Dict[str, str]]) -> bool:
    """Check if any users already exist in the database

    Args:
        user_list: The list of users to check

    Returns:
        True if any users already exist, otherwise False
    """
    for user in user_list:
        if user_exists(user['user_id']):
            return True

    return False


def user_exists(user_id: str) -> bool:
    """Check if the user exists in the database.

    Returns:
        True if the user exists, otherwise False
    """

    result: bool = False
    try:
        user = User.objects.get(user_id=user_id)
        return bool(user)
    except Exception:
        # User does not exist
        pass

    return result


# TODO(egeldenhuys): keep track of file uploads. Confirm


@admin_required
def submit_csv(request) -> HttpResponse:
    """Validate the CSV and return the status and data in the context

    Note:
        Saves the file to ./media/documents
        The file is only deleted here when not valid.
        confirm_csv() is responsible for deleting valid files.
        Files that are not confirmed or cancelled the file is
        not deleted.

    Context Args:
        doc_file (FILE): The CSV file that was uploaded

    Context Returns:
        message (str): A message indicating the error, if not valid
        possible_users (List[Dict[str, str]]):
            A list of users to be added, or already existing, if valid
        request_id (str): The name of the uploaded file, if valid
        error_code (int):
            0: No error
            1: CSV error
            2: User(s) already exists
            3: CSV upload error

        `error_code` will always be returned.
    """
    # TODO(egeldenhuys): Get fields from User Model
    fields: list = [
        'title', 'initials', 'name', 'surname', 'cell', 'email', 'user_id'
    ]

    page_context_data: Dict[str, Any] = init_context_data()
    csv_context: Dict[str, Any] = page_context_data['csv_upload_args']
    csv_context['error_code'] = 3

    if request.method == 'POST' and \
            DocumentForm(request.POST, request.FILES).is_valid():

        csv_file = Document(doc_file=request.FILES['doc_file'])

        csv_file.save()

        # [1:] Strip the leading /
        file_path: str = csv_file.doc_file.url[1:]

        result: CsvStatus = csv_utils.validate_csv(fields, file_path=file_path)

        if result.valid:
            existing_users: List[Dict[str, str]] = list()

            for user in result.data:
                if user_exists(user['user_id']):
                    existing_users.append(user)

            if existing_users:
                csv_context[
                    'message'] = 'The following user_id(s) already exist'
                csv_context['possible_users'] = existing_users
                csv_context['error_code'] = 2
            else:
                csv_context[
                    'message'] = 'The CSV file is valid. The following users will be added:'
                csv_context['possible_users'] = result.data
                csv_context['error_code'] = 0
                csv_context['request_id'] = path_leaf(csv_file.doc_file.url)
        else:
            csv_context['message'] = result.error_message
            csv_context['error_code'] = 1

        if csv_context['error_code'] != 0 and csv_context['error_code'] != 3:
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        csv_context['message'] = 'Error uploading document. Please try again'
        csv_context['error_code'] = 1

    return render(request, 'peer_review/userAdmin.html', page_context_data)
