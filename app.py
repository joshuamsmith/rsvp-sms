"""
X 1. Allow Admins to push poll to members
X 2. Allow Admins to push poll reminder to Members who have not yet RSVP'd
3. Add STANDBY list of favorable subs to push invite to them with limited space available
X 4. Update Admins if member changes RSVP
X 5. Send non-RSVP responses from Members to Admins
X 6. Allow members to RSVP for their guest subs
7. Shame members that change their RSVP to "No" within x hours
X 8. Allow Admins to send out messages to list for updates or fee collections

"""

# DB schema
# Member = "1": {"name": "Josh", "phone": "+19168357536"}
# Game = "17": {"game": 1503630000, "timestamp": 1503639064, "sub": "2", "name": "Testman", "reply": "yes"}

import arrow
from tinydb import TinyDB, Query

import config
import re
import sms


def main(phone, message):
    result = re.search('^[a-zA-Z]', message)
    try:
        command = result.group(0).lower()
        if command in ['y', 'n', 'yes', 'no']:
            return update_rsvp(phone, message)
        elif command in ['l']:
            return send_rsvp_status(get_next_game())
        else:
            # 5. Send non-RSVP responses from Members to Admins
            member = get_member(phone)
            return notify_admin("{} said: {}".format(member['name'], message))
    except AttributeError:
        pass

    if is_admin(phone):
        result = re.search('^([?!])\s?(.*)', message)
        try:
            command = result.group(1)
            message = result.group(2)
            return admin_commands['command_' + command](message)
        except AttributeError:
            pass
    return None


# 8. Allow Admins to send out messages to list for updates or fee collections
def member_broadcast(message):
    if message.strip():
        members = get_members()
        for member in members:
            send_message(member, message)
        return 'Member broadcast sent: "{}"'.format(message)
    return 'Message not sent'


# 1. Allow Master Member to push poll to members
def send_invite(members=None):
    # Include list of Members to send to specific people (aka those not yet RSVP's).
    #  Otherwise, send to all Members.

    # create message
    next_game = get_next_game()
    message = "will you be playing this {} at {}? Please reply with a 'yes' or 'no'. " \
              "Add a number after if you're bringing a guest: 'yes 2' for two subs.".format(next_game.format('dddd'),
                                                                                            next_game.format('h:mm A'))
    if members is None:
        # get all members from list
        members = get_members()

    # send message to each member
    for member in members:
        if not config.testing:
            send_message(member, '{}, '.format(member['name'], message))
        else:
            print('{}, '.format(member['name']) + message)

    # acknowledge invite was sent
    return "RSVP poll has been sent to {} players.".format(len(members))


# 1.1 Handle user's RSVP response
def update_rsvp(phone, message):
    # get member by phone and ...
    members = get_members()
    Member = Query()
    results = members.search(Member.phone == phone)
    if len(results) == 1:
        member = results[0]
    else:
        return 'ERROR: Search results invalid'
    # ... upcoming game
    game = get_next_game()
    # quantify response
    command = re.search(r"^([a-zA-Z]*)\s?(\d)?", message)
    if command.group(1).lower() in ['y', 'yes']:
        reply = 'yes'
    elif command.group(1).lower() in ['n', 'no']:
        reply = 'no'
    else:
        # error
        return 'ERROR: Not a valid response: "{}"'.format(command.group(1))
    sub = command.group(2)
    rsvp_message = reply.capitalize()
    if sub:
        rsvp_message += ' with {} sub(s)'.format(sub)
    set_rsvp(game, member, reply, sub)
    return 'Thank you for RSVPing {} to the next game!'.format(rsvp_message)


def set_rsvp(game, member, reply, sub):
    # check for current RSVP
    db = TinyDB(config.db_file)
    rsvps = db.table('RSVP')
    RSVP = Query()
    results = rsvps.search((RSVP.game == game.timestamp) & (RSVP.name == member['name']))
    rsvp = {}  # dict for insert/update
    # Check for existing RSVP and note any changes
    if len(results) > 0:
        # We'll have to get all replies and then sort to find newest one
        newest_reply = max(results, key=lambda r: r['timestamp'])
        if reply != newest_reply['reply'] or sub != newest_reply['sub']:
            # notify Admins of change
            notify_admin('{} changed RSVP to {} with {} subs!'.format(member['name'], reply,
                                                                      sub if sub is not None else 0))
        else:
            print('RSVP is the same')
    # Add/Update RSVP reply
    rsvp = {'name': member['name'], 'game': game.timestamp, 'reply': reply, 'sub': sub,
            'timestamp': arrow.now().timestamp}
    rsvps.insert(rsvp)


# 1.2 Let members see RSVP list
def get_game_rsvps(game):
    db = TinyDB(config.db_file)
    rsvps = db.table('RSVP')
    Rsvp = Query()
    results = rsvps.search(Rsvp.game == game.timestamp)
    players = {}  # string to return for testing
    for player in results:
        if 'name' not in players or players['name'] is None:
            players[player['name']] = player
        elif player['timestamp'] > players[player['name']]['timestamp']:
            players[player['name']] = player
    return players


def send_rsvp_status(game):
    players = get_game_rsvps(game)
    response = ''
    spots = {'yes': 0, 'no': 0, 'sub': 0}
    for key, rsvp in players.items():
        spots[rsvp['reply']] += 1
        response += '{}: {}'.format(rsvp['name'], rsvp['reply'].capitalize())
        if rsvp['sub'] and int(rsvp['sub']) > 0:
            spots['sub'] = spots['sub'] + int(rsvp['sub'])
            response += ' and is bringing {} sub{}'.format(rsvp['sub'], 's' if int(rsvp['sub']) > 1 else '')
        response += "\n"
    response = "Yes: {} No: {} Subs: {} (Total Players: {})\n --- --- --- \n{}".format(spots['yes'], spots['no'],
                                                                                       spots['sub'],
                                                                                       spots['yes'] + spots['sub'],
                                                                                       response)
    if config.testing:
        response = "!"*20 + "\n!! TEST TEST TEST !!\n" + "!"*20 + "\n" + response
    return response


# 2. Allow Admins to push poll reminder to Members who have not yet RSVP'd
def send_reminder(*args):
    # get list of Members that haven't RSVP'd
    all_members = get_members()
    game = get_next_game()
    rsvpd_players = get_game_rsvps(game)
    members = [member for member in all_members if member['name'] not in rsvpd_players]
    # send message to those Members
    return send_invite(members)


# 4. Update Admins if member changes RSVP
def notify_admin(message):
    for admin in get_admins():
        send_message(admin, message)


# Utility Functions
def send_message(member, message):
    if not config.testing:
        sms.send_sms(member['phone'], message)
    else:
        print('Sending to {}:'.format(member['name']), message)
    pass


def is_admin(phone):
    results = get_member(phone)
    if not results:
        # phone number doesn't belong to a member
        return False
    db = TinyDB(config.db_file)
    admin_tbl = db.table('Admin')
    # is that Member in Admin list?
    if results[0]['name'] in [_['name'] for _ in admin_tbl.all()]:
        # Member is in Admin group
        return True
    return False
    # Member was not found in Admin group


def get_admins():
    members = get_members()
    admins = [member for member in members if is_admin(member['phone'])]
    return admins


def is_member(phone):
    results = get_member(phone)
    if not results:
        # phone number doesn't belong to a member
        return False
    return True


def get_member(phone):
    db = TinyDB(config.db_file)
    member_tbl = db.table('Member')
    # does the Phone match a Member
    Member = Query()
    results = member_tbl.search(Member.phone == phone)
    if len(results) != 1:
        return False
    return results


def get_members():
    db = TinyDB(config.db_file)
    members = db.table('Member')
    return members


def get_next_game(game_date=None):  # returns Arrow object for next game
    if game_date is None:
        today = arrow.now()
        # find days till next game day. If today is game day, return zero.
        days_till_game = config.event_weekday - today.isoweekday()
        # adjust date to next game date
        if days_till_game < 0:
            days_till_game += 7
        next_game = today.shift(days=days_till_game)
    else:
        next_game = arrow.get(game_date, 'YYYY-MM-DD', tzinfo='US/Pacific')

    # adjust to next game time
    next_game = next_game.replace(hour=config.event_hour, minute=config.event_minute)
    return next_game.floor('minute')


member_commands = {

}

admin_commands = {
    'command_?': send_reminder,
    'command_!': member_broadcast
}


if __name__ == '__main__':
    print('Running script...')
