# Download the twilio-python library from http://twilio.com/docs/libraries
from twilio.rest import Client

# get module config values
import config

# Find these values at https://twilio.com/user/account
account_sid = config.account_sid
auth_token = config.auth_token
client = Client(account_sid, auth_token)
DID_from = config.DID_from


def send_sms(DID_to, body):
    message = client.messages.create(to=DID_to, from_=DID_from, body=body)
