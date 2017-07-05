from flask import Flask, request, redirect
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse

import program

app = Flask(__name__)


@app.route("/dweb/", methods=['GET', 'POST'])
def hello_monkey():
    """Respond and greet the caller by name."""

    from_number = request.values.get('From', None)
    if from_number in program.get_member_list():
        body = request.values.get('Body', None)
        DID = request.values.get('From')
        message = Message()
        message.body(program.poll_action(DID, body))
#        message = program.MEMBER_LIST[from_number] + ", thanks for the message!"
    else:
        return None

    resp = MessagingResponse()
    resp.append(message)

    return str(resp)


if __name__ == "__main__":
    app.run(debug=True, port=6543)
