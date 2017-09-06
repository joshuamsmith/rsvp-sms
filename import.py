###
# Import RSVP history from previous games via CSV files
##
import app


def main(game_date=None):
    if game_date is None:
        # process files in ./rsvps/ dir
        pass
    else:
        game_datetime = app.get_next_game(game_date)
        # look for <game_date>.csv file in ./rsvps/
        with open('./rsvps/{}.csv'.format(game_date), 'r') as f:
            history = f.readlines()

        for response in history[1:]:
            phone, player, rsvp = response.strip().split(',')
            if rsvp == 'y':
                rsvp = 'yes'
            else:
                rsvp = 'no'
            member = {'name': player, 'phone': phone}
            app.set_rsvp(game_datetime,  member, rsvp, 0)
            # print('{} said {} to game'.format(player, rsvp))


if __name__ == '__main__':
    game_date = '2017-09-07'
    print('### updating db ###')
    main(game_date)
    print('### results ###')
    print(app.send_rsvp_status(app.get_next_game(game_date)))
    # print(app.config.testing)

    pass
