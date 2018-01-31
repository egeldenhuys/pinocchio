import csv
import os
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import render
from peer_review.decorators.adminRequired import admin_required
from peer_review.forms import DocumentForm, UserForm
from peer_review.models import User, Document
from peer_review.view.userFunctions import user_error
from peer_review.view.userManagement import create_user_send_otp
from typing import List, Dict
from peer_review.modules.csvUtils import CsvStatus

import peer_review.modules.csvUtils as csv_utils

""" Process
# CSV Upload:
    1. User sends CSV file in Post request. validate_csv()
    2. We validate the CSV file and send back:
        - The user list for a preview
        - Error messages
        The user list object should now be in browser memory
    3. User clicks Confirm button. User_list is sent back to server
        Users are added and validity confirmed yet again.
        - Report error or success


validate_csv(csv_path: str) -> render
confirm(user_list: List[Dict[str, str]]) -> render


"""


def validate_csv(csv_path: str) -> HttpResponse:
    pass

def confirm_csv(user_list: List[Dict[str, str]]) -> HttpResponse:
    pass

"""
                                         {'message': message,
                                           'error': error_type,
                                           'users': users,
                                           'userForm': user_form,
                                           'docForm': doc_form,
'email_text': email_text})

"""


def init_context_data() -> Dict[str, object]:
    """Return context data required for the page to function"""
    context_data: Dict[str, object] = dict()

    context_data['users'] = User.objects.all
    context_data['user_form'] = UserForm()
    context_data['docForm'] = DocumentForm()

    module_dir = os.path.dirname(__file__)
    file_path = os.path.join(module_dir)

    with open(file_path + '/../text/otp_email.txt', 'r+') as file:
        context_data['email_text'] = file.read()

    return context_data


@admin_required
def submit_csv(request):
    # TODO(egeldenhuys): Get fields from User Model
    fields: list = [
        'title', 'initials', 'name', 'surname', 'cell', 'email', 'user_id'
    ]

    context_data: Dict[str, object] = init_context_data()

    # TODO(egeldenhuys): Check what is_valid() actually checks
    if request.method == 'POST' and \
            DocumentForm(request.POST, request.FILES).is_valid():

        csv_file = Document(doc_file=request.FILES['doc_file'])

        # TODO(egeldenhuys): What happens with saved files?
        # Perhaps we need to save them to tmp.

        csv_file.save()

        # [1:] Strip the leading /
        result: CsvStatus = csv_utils.validate_csv(fields, file_path=csv_file.doc_file.url[1:])

        # TODO(egeldenhuys): Check for duplicate users

        if result.valid == True:
            context_data['message'] = None
            context_data['possible_users'] = result.data
        else:
            context_data['message'] = result.error_message
            context_data['error_code'] = 0
    else:
        context_data['message'] = 'Error uploading document'
        context_data['error_code'] = 0

    return render(request, 'peer_review/userAdmin.html', context_data)
