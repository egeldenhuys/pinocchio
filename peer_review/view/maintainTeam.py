import csv
import os
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from ..models import User, RoundDetail, TeamDetail, Document
from peer_review.decorators.adminRequired import admin_required
from peer_review.forms import DocumentForm
from peer_review.view.userFunctions import user_error
from django.template import loader

from django.http import HttpResponse
from typing import List, Dict, Any
from peer_review.modules.csv_utils import CsvStatus
import peer_review.modules.csv_utils as csv_utils
import  django.core.exceptions



'''
Checks:
- All users should exist
    - If not exist, display the list of invalid user_ids
    - Abort
- The round should exist
    - If not exist, display error message
    - Abort
- The team should exist
    - If not exist, display teams that will be created
    - If confirm, create teams and continue
- A user should not be part of a team
    - If part of team, display error of offending line
    - Abort
- If all checks pass, then ask for confirmation

Process:
- Upload CSV.
    - Save to /media. See CSV upload for user CSV
- Perform checks
    - If we need to abort, delete the CSV file and return prompt
    - If all checks pass, wait for confirmation
- If confirm
    - Parse again to verify system state
    - Perform actions
    - Delete CSV
- If Cancel by admin
    - Delete CSV
    
Note:
- If admin does not confirm, or cancel then the CSV will not be deleted

Actions to be performed on confirmation:
    The following teams will be created under the round "<Round ID>"
    
    TripleParity
        - Evert
        - Raymond
        
    TeamPython
        - Bob
        - Fred
'''


def init_context_data() -> Dict[str, any]:
    """Get the context required for the template to function

    :return: Context dict
    """
    context: Dict[str, any] = {'users': User.objects.filter(Q(is_active=1) & (Q(status='S') | Q(status='U'))),
               'rounds': RoundDetail.objects.all(),
               'teams': TeamDetail.objects.all(),
               'docForm': DocumentForm()}
    return context


@admin_required
def maintain_team(request):
    context = init_context_data()

    if request.method == "POST":
        round_pk = request.POST.get("roundPk")
        context['preselectedRoundPk'] = int(round_pk)

    return render(request, 'peer_review/maintainTeam.html', context)


@admin_required
def change_team_status(request, team_pk, status):
    team = get_object_or_404(TeamDetail, pk=team_pk)
    team.status = status
    team.save()
    return JsonResponse({'success': True})


@admin_required
def change_user_team_for_round(request, round_pk, user_id, team_name):
    try:
        team = TeamDetail.objects.filter(user_id=user_id).get(roundDetail_id=round_pk)
    except TeamDetail.DoesNotExist:
        team = TeamDetail(
            user=get_object_or_404(User, user_id=user_id),
            roundDetail=get_object_or_404(RoundDetail, pk=round_pk)
        )

    team.teamName = team_name
    if team_name == 'emptyTeam':
        team.delete()
    else:
        team.save()
    return JsonResponse({'success': True})


@admin_required
def get_teams_for_round(request, round_pk):
    teams = TeamDetail.objects.filter(roundDetail_id=round_pk)
    response = {"users": {},
                "teamTables": {},
                "teams": []}
    team_sizes = {}
    team_tables = {}
    for team in teams:
        if team.teamName not in team_sizes:
            team_sizes[team.teamName] = 0
        team_sizes[team.teamName] += 1

    for team in teams:
        if team.teamName not in team_tables:
            team_tables[team.teamName] = []

        team_tables[team.teamName].append(team.user)
        response["users"][team.user.user_id] = True

    for userList in team_tables:
        template = loader.get_template('peer_review/maintainTeam-teamPanel.html')
        context = {
            'team_name': userList,
            'userList': team_tables[userList],
            'team_size': team_sizes[userList],
        }
        new_team = template.render(context, request)
        response['teamTables'][userList] = new_team
        response['teams'].append(userList)
    # print(response)
    return JsonResponse(response)


@admin_required
def get_new_team(request, team_name):
    template = loader.get_template('peer_review/maintainTeam-teamPanel.html')
    context = {
        'team_name': team_name,
        'userList': [],
        'team_size': 0,

    }
    response = {'success': True, 'team': template.render(context, request)}
    return JsonResponse(response)


@admin_required
def get_teams(request):
    response = {}
    if request.method == "GET":
        teams = TeamDetail.objects.all()
        for team in teams:
            try:
                user = User.objects.get(pk=team.user.pk)
            except User.DoesNotExist:
                return JsonResponse("Team has a user which doesn't exist")
            response[team.pk] = {
                'user_id': user.user_id,
                'initials': team.user.initials,
                'surname': team.user.surname,
                'round': team.roundDetail.name,
                'team': team.teamName,
                'status': team.status,
                'teamId': team.pk,
            }
    elif request.method == "POST":
        user_pk = request.POST.get("pk")
        user = get_object_or_404(User, pk=user_pk)

        teams = TeamDetail.objects.filter(user=user)
        for team in teams:
            response[team.pk] = {
                'round': team.roundDetail.name,
                'team': team.teamName,
                'status': team.status,
                'teamId': team.pk,
                'roundPk': team.roundDetail.pk
            }
    return JsonResponse(response)


@admin_required
def add_team_csv_info(team_list):
    try:
        for row in team_list:
            user_det_id = User.objects.get(user_id=row['user_id']).pk
            round_det_id = RoundDetail.objects.get(name=row['roundDetail']).pk
            change_user_team_for_round("", round_det_id, user_det_id, row['teamName'])
        return 1
    except User.DoesNotExist:
        return "One of the Users does not exist"
    except RoundDetail.DoesNotExist:
        return "One of the Rounds does not exist"


@admin_required
def submit_team_csv(request):
    if not request.user.is_authenticated():
        return user_error(request)

    global error_type
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            new_doc = Document(doc_file=request.FILES['doc_file'])
            new_doc.save()

            file_path = new_doc.doc_file.url
            file_path = file_path[1:]

            team_list = list()
            error = False

            count = 0
            with open(file_path) as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    count += 1
                    valid = validate_team_csv(row)
                    if valid == 0:
                        print(row['user_id'])
                        team_list.append(row)
                    else:
                        message = "Oops! Something seems to be wrong with the CSV file at row " + str(count) + "."

                        row_list = list()
                        try:
                            row_list.append(row['user_id'])
                            row_list.append(row['round_name'])
                            row_list.append(row['team_name'])
                        except KeyError:
                            valid = 4

                        if valid == 1:
                            error_type = "Incorrect number of fields."
                        elif valid == 2:
                            error_type = "Not all fields contain values."
                        elif valid == 4:
                            error_type = "One of these headers does not exist, 'user_id', 'round_name', or 'team_name'."

                        os.remove(file_path)
                        return render(request, 'peer_review/csvTeamError.html',
                                      {'message': message, 'row': row_list, 'error': error_type})
        else:
            message = "Oops! Something seems to be wrong with the CSV file."
            error_type = "No file selected."
            return render(request, 'peer_review/csvTeamError.html', {'message': message, 'error': error_type})

        if not error:
            add_team_csv_info(team_list)
    return HttpResponseRedirect('../')


def validate_team_csv(row):
    # 0 = correct
    # 1 = incorrect number of fields
    # 2 = missing value/s
    # 3 = incorrect format

    if len(row) != 3:
        return 1
    for key, value in row.items():
        if value is None:
            return 2
    return 0


class Team(object):
    def __init__(self, team_name: str, team_members: List[str]):
        self.team_name = team_name
        self.team_members = team_members


class Round(object):
    def __init__(self, teams: Team):
        self.teams = teams


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
            1: CSV error. (Missing fields, error decoding, headers).
                Message returned by the csv_utils module
            2: CSV Upload Error
            3: Round ID does not exist
            4: User does not exist
            5:

        `error_code` will always be returned.
    """
    # TODO(egeldenhuys): Get fields from a model(s) in the database
    fields: list = [
        'user_id', 'round_name', 'team_name'
    ]

    optional_fields: list = []

    context_data: Dict[str, Any] = init_context_data()
    context_data['error_code'] = 3

    if request.method == 'POST' and \
            DocumentForm(request.POST, request.FILES).is_valid():

        csv_file = Document(doc_file=request.FILES['doc_file'])

        csv_file.save()

        # [1:] Strip the leading /
        file_path: str = csv_file.doc_file.url[1:]

        result: CsvStatus = csv_utils.validate_csv(fields,
                                                   file_path=file_path,
                                                   primary_key_field='user_id',
                                                   optional_fields=optional_fields)

        if result.valid:

            # Place each user into a team, and each team into a round

            for row in result.data:
                print(row['user_id'])

    else:
        context_data['message'] = 'Error uploading document. Please try again'
        context_data['error_code'] = 1

    return render(request, 'peer_review/maintainTeam.html', context_data)


@admin_required
def confirm_csv():
    return False;