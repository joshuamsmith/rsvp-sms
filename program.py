#!/usr/bin/python
"""
Objective: This program will serve to increase RSVP participation and response speed for the
Thursday night basketball games at Daniel Webster Middle School.
Flow: When run, program will send out an SMS message to each member of group asking them to respond
to the text message with a "Y" or "N" to if they will be playing this week. Subsequent responses of "Y"
or "N" will update their RSVP for this week's game. "L" will be an option for them to get a LIST of
current RSVP status for members that have responded.
Roadmap:
X 1. Allow Master Member to push poll to members by sending a text with next game's date.
X 2. Allow Master Member to push poll reminder to Members who have not yet RSVP'd
3. Add STANDBY list of favorable subs to push invite to them with limited space available
X 4. Update Master Members if member changes RSVP
X 5. Send non-RSVP responses from Members to Master Members
6. Allow members to RSVP for their guest subs
"""

import csv
import datetime
import configparser
import os

import sms

# get module config values
import config

# Database: I will be using a text flat file to keep track of responses. One file per weekly game.

# MEMBER_LIST: A Dict of Member cell phone numbers and their name. {cell phone number, name}
MEMBER_LIST = config.MEMBER_LIST

SUB_LIST = {}


def get_member_list():
    return MEMBER_LIST


# MASTER_MEMBER: Member in charge of organizing games.
MASTER_MEMBERS = config.MASTER_MEMBERS

RESPONSE_TYPES = {'n': 'No', 'y': 'Yes'}
FIELDNAMES = 'phone_number,name,rsvp'.split(',')
Thursday = 4
game_time = None


def get_game_time():
    today = datetime.date.today()
    day_of_the_week = today.isoweekday()
    days_till_game = None
    # When is next game? Today = x, # of days in week = 7, Game day (Thursday) = 4
    if day_of_the_week - Thursday > 0:
        # of days till next game is (7-x)+4
        days_till_game = (7 - day_of_the_week) + Thursday
    elif Thursday - day_of_the_week > 0:
        days_till_game = Thursday - day_of_the_week
    # else: #Today is Thursday
    # if it is Thursday before game time, give today's date
    # if it is Thursday after game time, give next Thursday's date

    if days_till_game:
        game_time = datetime.datetime.combine(today + datetime.timedelta(days_till_game), datetime.time(hour=20))
    else:
        game_time = datetime.datetime.combine(today, datetime.time(hour=20))

    return game_time


def get_rsvp_file():
    return os.path.abspath(os.path.join('.', 'rsvps', get_game_time().date().isoformat() + '.csv'))


def send_poll(poll_member_dict):
    # Prep polling message
    rsvp_request = '{}, will you be playing basketball this Thursday? [Y]es or [N]o'
    for DID, player in poll_member_dict.items():
        sms.send_sms(DID, rsvp_request.format(player))


def csv_dict_writer(fout, fieldnames, data):
    writer = csv.DictWriter(fout, delimiter=',', fieldnames=fieldnames)
    writer.writeheader()
    if data:
        for row in data:
            writer.writerow(row)


def csv_dict_reader(fin):
    reader = csv.DictReader(fin, delimiter=',')
    return reader


def send_sms_to_masters(message):
    for DID, name in MEMBER_LIST.items():
        if name in MASTER_MEMBERS:
            sms.send_sms(DID, message)


def rsvp_update(caller_did, rsvp_reply):
    # caller_did: string containing cell phone number of member
    # rsvp_reply: string containing a 'y' or 'n' response to rsvp request
    # Read in Game file
    rsvp_list = get_rsvp_list()
    # Update/Add RSVP for caller
    # - Check for update, if so, notify Admin(s)
    if caller_did in rsvp_list.keys() and rsvp_reply != rsvp_list[caller_did]['rsvp']:
        send_sms_to_masters('{} has changed RSVP from {} to {}'.format(MEMBER_LIST[caller_did],
                                                                       rsvp_list[caller_did]['rsvp'], rsvp_reply))
    rsvp_list[caller_did] = {'name': MEMBER_LIST[caller_did], 'rsvp': rsvp_reply}
    update_list = []
    for member_did in rsvp_list:
        data_list = [member_did, rsvp_list[member_did]['name'], rsvp_list[member_did]['rsvp']]
        # add Dict to List for updates
        update_list.append(dict(zip(FIELDNAMES, data_list)))
    with open(get_rsvp_file(), 'w', newline='') as fout:
        # update file with rsvp details
        csv_dict_writer(fout, FIELDNAMES, update_list)
    # Thank them for response
    return "Thank you for RSVPing '{}' to the next game on {}!\nYou can update your RSVP by sending a 'Y' or 'N'." \
           " Or see the RSVP list by sending 'L'.".format(RESPONSE_TYPES[rsvp_reply], get_game_time().
                                                          strftime("%A (%b. %d) at %I:%M %p!"))


def get_rsvp_list():
    rsvp_list = {}
    with open(get_rsvp_file(), 'r') as csvfile:
        csvreader = csv_dict_reader(csvfile)
        for entry in csvreader:
            rsvp_list[entry['phone_number']] = {'name': entry['name'], 'rsvp': entry['rsvp']}
    return rsvp_list


def send_list():
    message = ''
    y = 0
    n = 0
    rsvp_list = get_rsvp_list()
    for member in rsvp_list.values():
        message += ''.join([member['name'], ': ', RESPONSE_TYPES[member['rsvp']], '\n'])
        if 'y' == member['rsvp']:
            y += 1
        else:
            n += 1
    message = "There are {} 'Yes' and {} 'No' RSVPs:\n{}".format(y, n, message)
    return message


def start_poll():
    # Start polling process:
    # todo: check if poll file already exists, notify user if so
    if os.path.isfile(get_rsvp_file()):
        return "Poll already exists, please use '!' to nag Members."
    # create poll file
    with open(get_rsvp_file(), 'w', newline='') as fout:
        csv_dict_writer(fout, FIELDNAMES, data=False)
    # Send Poll
    send_poll(MEMBER_LIST)
    return "Poll has been sent!"


def send_nag():
    # collect all Members that have not RSVP'd yet
    rsvp_member_list = get_rsvp_list()
    not_rsvp_member_list = rsvp_member_list.keys() ^ MEMBER_LIST.keys()
    # send additional RSVP request to these Members
    not_rsvp_member_dict = {}
    for member_DID in not_rsvp_member_list:
        not_rsvp_member_dict[member_DID] = MEMBER_LIST[member_DID]
    # send nag poll
    send_poll(not_rsvp_member_dict)
    return "The following Members have not RSVP'd: {}. Sending reminder now!".format(
        ", ".join(not_rsvp_member_dict.values()))


def poll_action(caller_did, body):
    message = "NO ACTION TAKEN."
    body = body.lower().strip()
    # IF 'Y' or 'N' set/update their RSVP
    if body == 'y' or body == 'yes' or body == 'n' or body == 'no':
        message = rsvp_update(caller_did, body[0])
    # IF 'L' send Member the current RSVP response list
    elif body == 'l' or body == 'list':
        message = send_list()  # Catch message from Master:
    # IF '?' and is in MASTER_MEMBER list then start a Poll for upcoming Thursday at 8pm
    elif body == '?' and MEMBER_LIST[caller_did] in MASTER_MEMBERS:
        message = start_poll()
    # IF '!' and is in MASTER_MEMBER list then send Nag to members who do not have an entry in Game file
    elif body == '!' and MEMBER_LIST[caller_did] in MASTER_MEMBERS:
        message = send_nag()
    else:
        send_sms_to_masters(body)
        message = "Non-RSVP message sent."

    return message


if __name__ == "__main__":
    command = input("What is your command? ")
    caller_did = config.test_caller_id
    print(poll_action(caller_did, command))
