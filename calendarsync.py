from __future__ import print_function
from asyncio import events

import datetime
import os.path
from tkinter import LAST
from venv import create

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_ADDRESSES = {'xx'}
LAST_UPDATE_DATE = datetime.datetime.strptime('2022-01-01','%Y-%m-%d').date()


def create_shadow(creds):
    try:
        service = build('calendar', 'v3', credentials=creds)

        page_token = None
        while True:
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            shadowId = None
            for calendar_list_entry in calendar_list['items']:
                if calendar_list_entry['summary'] == 'Shadow':
                    shadowId = calendar_list_entry['id']
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break

        if shadowId:
            print('Shadow calendar exists with id {}'.format(shadowId))
            return shadowId
        # else:
            # create calendar

    except HttpError as error:
        print('An error occurred: %s' % error)

def get_events(creds, calId, daysFromToday, createdEvents):
    try:
        service = build('calendar', 'v3', credentials=creds)

        ls_events = []

        page_token = None
        while True:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events = service.events().list(calendarId=calId, pageToken=page_token, timeMin = now).execute()

            for event in events['items']:

                if ('start' in event) & ('attendees' in event):
                    if 'dateTime' in event['start']:
                        event_date = datetime.datetime.strptime(event['start']['dateTime'],'%Y-%m-%dT%H:%M:%S%z').date()
                    elif 'date' in event['start']:
                        event_date = datetime.datetime.strptime(event['start']['date'],'%Y-%m-%d').date()
                    else:
                        event_date = datetime.datetime.strptime('9999-12-31','%Y-%m-%d').date()

                    if 0 <= ((event_date - datetime.date.today()).days) <= daysFromToday:
                        event_attendee_to_exclude = []
                        for attendee in event['attendees']:
                            if attendee['email'] in CLIENT_ADDRESSES:
                                event_attendee_to_exclude.append(attendee['email'])
                        if event['organizer']['email'] in CLIENT_ADDRESSES:
                            event_attendee_to_exclude.append(event['organizer']['email'])

                        if createdEvents:
                            relevant_date = datetime.datetime.strptime(event['created'][0:10],'%Y-%m-%d').date()
                        else:
                            relevant_date = datetime.datetime.strptime(event['updated'][0:10],'%Y-%m-%d').date()

                        if relevant_date > LAST_UPDATE_DATE:
                            new_event = {}
                            new_event['summary'] = 'busy'
                            new_event['description'] = 'Hi Jackie, This is to sync you calendar. Best regards, JST \
                            Original description: {} \
                            ID = {}'.format(event['summary'], event['id'])


                            elements_attendees = CLIENT_ADDRESSES.difference(set(event_attendee_to_exclude))
                            attendees = []
                            for el in elements_attendees:
                                attendee = {}
                                attendee['email'] = el
                                attendees.append(attendee)
                            attendee = {}


                            new_event['attendees'] = attendees

                            start = {}
                            start['dateTime'] = event['start']['dateTime']
                            start['timeZone'] = event['start']['timeZone']
                            new_event['start'] = start

                            end = {}
                            end['dateTime'] = event['end']['dateTime']
                            end['timeZone'] = event['end']['timeZone']
                            new_event['end'] = end

                            new_event['visibility'] = 'private'
                            new_event['guestsCanSeeOtherGuests'] = False
                            #print(new_event)
                            ls_events.append(new_event)



            page_token = events.get('nextPageToken')

            if not page_token:
                break

        return ls_events

    except HttpError as error:
        print('An error occurred: %s' % error)


def insert_events(creds, events, calId):
    try:
        service = build('calendar', 'v3', credentials=creds)

        for e in events:
            event = service.events().insert(calendarId=calId, body=e).execute()
            print('Event created: %s' % (event.get('htmlLink')))

    except HttpError as error:
        print('An error occurred: %s' % error)

def get_credentials():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

if __name__ == '__main__':
    # get credentials
    creds = get_credentials()

    # create calendar shadow if not exists, retrieve its id
    shadowId = create_shadow(creds)

    # get all events of next time period from today (in days)
    events_created = get_events(creds, 'primary', 3, True)
    print(events_created)
    print(len(events_created))

    # insert new created events into shadow calendar
    insert_events(creds, events_created, shadowId)


    # get list of updated events


    # get id's of those updated events from shadow calendar
