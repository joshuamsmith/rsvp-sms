from flask import Flask, request, redirect
from tinydb import TinyDB, Query
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse

import app
import config

wsgi = Flask(__name__)


@wsgi.route("/dweb/", methods=['GET', 'POST'])
def hello_monkey():
    phone_from = request.values.get('From', None)
    if app.is_member(phone_from):
        body = request.values.get('Body', None)
        message = Message()
        message.body(app.main(phone_from, body))
    else:
        return None

    resp = MessagingResponse()
    resp.append(message)

    return str(resp)


def init_db():
    db = TinyDB(config.db_file)
    if len(db.tables()) > 1:
        return True
    member_table = db.table('Member')
    member_table.insert_multiple(config.member_list)
    admin_table = db.table('Admin')
    admin_table.insert_multiple(config.admin_members)

if __name__ == "__main__":
    # Load and check DB
    init_db()
    wsgi.run(debug=True, port=6543)
