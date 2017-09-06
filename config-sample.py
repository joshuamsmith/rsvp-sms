#!/usr/bin/python

testing = True

# for program.py
if not testing:
    member_list = [
        {'phone': '+15555555555', 'name': 'Josh'}
    ]
    admin_members = [{'name': 'Josh'}]
    db_file = 'prod.db'
else:
    member_list = [
        {'name': 'Testman', 'phone': '+15555555555'}
    ]
    admin_members = [{'name': 'Testman'}]
    db_file = 'dev.db'

event_weekday = 3  # day of the week (0 is Monday)
event_hour = 19  # military (24 hr)
event_minute = 30
test_caller_id = '+15555555555'

# for sms.py
account_sid = "xxx"
auth_token = "xxx"
DID_from = "+15555555555"
