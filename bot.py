from flask import Flask, request
import urllib3
import telepot
import random
from operator import itemgetter
from questions import questions_list
import _mysql
import myconf

proxy_url = myconf.proxy_url
telepot.api._pools = {
    'default': urllib3.ProxyManager(
        proxy_url=proxy_url,
        num_pools=3,
        maxsize=10,
        retries=False,
        timeout=30),
}

telepot.api._onetime_pool_spec = (
    urllib3.ProxyManager,
    dict(
        proxy_url=proxy_url,
        num_pools=1,
        maxsize=1,
        retries=False,
        timeout=30))

# Support structures and utilities
active_games = {}
active_players = {}
id_username = []
answers = {}
choices = {}
ranking = {}
broadcast_list = []
admin = myconf.admin
debug = True
bot_locked = False

secret = myconf.secret
bot = telepot.Bot(myconf.bot_key)
bot.setWebhook(
    myconf.webapp_url.format(secret),
    max_connections=1)
app = Flask(__name__)

bot.sendMessage(admin, "Bot started!")


def parse_update(update):
    return update["message"]["text"], update["message"]["chat"]["id"], update["message"]["from"]["first_name"]
    # testo, id, nome


def welcome(chat_id, username):
    bot.sendMessage(chat_id, "Benvenuto/a " + username + "! Questo bot ti permette di giocare a Fibbage assieme ai tuoi"
                             "amici, meglio se dal vivo. Usa /start_game per iniziare una nuova partita, oppure /join"
                             "[id] per entrare in un match.")


def lock_bot(chat_id):
    global bot_locked
    if chat_id == admin:
        bot_locked = not bot_locked
        if bot_locked:
            bot.sendMessage(admin, 'Bot is now locked for use.')
        else:
            bot.sendMessage(admin, 'Bot now unlocked.')


def toggle_debug(chat_id):
    global debug
    if chat_id == admin:
        debug = not debug
        bot.sendMessage(chat_id, "Debug: " + str(debug))
    else:
        bot.sendMessage(chat_id, "Non sei autorizzato ad utilizzare il debug.")


def send_debug_structures(chat_id):
    if chat_id == admin:
        bot.sendMessage(chat_id, 'Active games:')
        bot.sendMessage(chat_id, active_games)
        bot.sendMessage(chat_id, 'Active players:')
        bot.sendMessage(chat_id, active_players)
        bot.sendMessage(chat_id, 'Answers:')
        bot.sendMessage(chat_id, answers)
        bot.sendMessage(chat_id, 'Choices:')
        bot.sendMessage(chat_id, choices)
        bot.sendMessage(chat_id, 'ID/Username:')
        bot.sendMessage(chat_id, id_username)
        bot.sendMessage(chat_id, 'Classifica:')
        bot.sendMessage(chat_id, ranking)


def get_actives(chat_id):
    if chat_id == admin:
        bot.sendMessage(chat_id, active_players)
    else:
        bot.sendMessage(chat_id, "Non sei autorizzato a visualizzare la lista di giocatori attivi.")


def get_username(chat_id):
    for player in id_username:
        if chat_id == player[0]:
            return player[1]


def increase_score(chat_id, game_id, score):
    for player in ranking[game_id]:
        if chat_id == player[0]:
            player[1] += score

            db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
            db.query('UPDATE app_users SET user_score = user_score + ' + str(score) + ' WHERE user_id = '
                     + str(chat_id) + ';')
            db.close()


def increase_lies(chat_id, game_id):
    for player in ranking[game_id]:
        if chat_id == player[0]:
            player[2] += 1

            db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
            db.query('UPDATE app_users SET user_lies = user_lies + 1 WHERE user_id = ' + str(chat_id) + ';')
            db.close()


def increase_fails(chat_id, game_id):
    for player in ranking[game_id]:
        if chat_id == player[0]:
            player[3] += 1

            db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
            db.query('UPDATE app_users SET user_errors = user_errors + 1 WHERE user_id = ' + str(chat_id) + ';')
            db.close()


def increase_correct_ones(chat_id, game_id):
    for player in ranking[game_id]:
        if chat_id == player[0]:
            player[4] += 1

            db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
            db.query('UPDATE app_users SET user_corrects = user_corrects + 1 WHERE user_id = ' + str(chat_id) + ';')
            db.close()


def create_game(chat_id, username):
    game_id = random.randint(1, 1001)
    if chat_id in active_players:
        bot.sendMessage(chat_id, 'Sei già in una partita!')
    else:
        add_player_db(chat_id, username)
        active_games[game_id] = {'admin': chat_id, 'players': [chat_id], 'usernames': [username], 'phase': 0,
                                 'round': 1, 'questions': [],
                                 'seen': []}  # Questions contiene gli indici delle domande già utilizzate
        active_players[chat_id] = game_id
        answers[game_id] = []
        bot.sendMessage(chat_id,
                        'Hai creato la partita con ID ' + str(game_id) + '. Passa tale ID agli altri giocatori!')


def start_game(chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            choices[game_id] = []
            ranking[game_id] = []
            for player in active_games[game_id]['players']:
                ranking[game_id].append([player, 0, 0, 0,
                                         0])  # Nome utente, punteggio, numero di inganni,
                # numero di volte che si è stati ingannati, risposte corrette azzeccate
                bot.sendMessage(player, 'La partita è iniziata!')
                bot.sendMessage(player, '*Inizia un nuovo round! Round: 1\nIn questo round le bugie valgono 100 punti'
                                        'e la verità 500 punti.*', parse_mode='Markdown')
            break


def add_questions(text, chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            questions_to_add = text.strip('/add_questions ').split()
            try:
                for question in questions_to_add:
                    active_games[game_id]['seen'].append(int(question))
                bot.sendMessage(chat_id, 'Domande aggiunte alla lista di quelle già viste!')
                return
            except ValueError:
                bot.sendMessage(chat_id, 'Inserire una lista di domande valida! Esempio: 4 8 15 16 23 42')
    bot.sendMessage(chat_id, 'Non sei admin di alcuna partita!')


def join_game(text, chat_id, username):
    add_player_db(chat_id, username)
    game_id = text.strip('/join ')
    try:
        game_id = int(game_id)
        if chat_id in active_players:
            bot.sendMessage(chat_id, 'Sei già in una partita!')
        else:
            if game_id in active_games:
                if chat_id in active_games[game_id]['players']:
                    bot.sendMessage(chat_id, 'Sei già in tale partita!')
                else:
                    active_players[chat_id] = game_id

                    for player in active_games[game_id]['players']:
                        bot.sendMessage(player, username + ' si è unito alla partita!')

                    active_games[game_id]['players'].append(chat_id)
                    active_games[game_id]['usernames'].append(username)
                    bot.sendMessage(chat_id, 'Sei entrato nella partita con ID ' + str(game_id) + '!')
                    player_list = ''
                    for player in active_games[game_id]['usernames']:
                        player_list += player
                        player_list += ', '
                    bot.sendMessage(chat_id,
                                    'Giocatori attualmente in partita: ' + player_list[0:(len(player_list) - 2)])
            else:
                bot.sendMessage(chat_id, 'Non esiste alcuna partita con ID ' + str(game_id) + '!')
    except ValueError:
        bot.sendMessage(chat_id, 'Inserire un ID valido dopo /join!')


def end_game(chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            ranking_message = print_ranking(game_id, True)
            for player in active_games[game_id]['players']:
                bot.sendMessage(player, 'La partita con ID ' + str(game_id) + ' è terminata!')
                bot.sendMessage(player, ranking_message)
                active_players.pop(player)
            bot.sendMessage(chat_id, 'Le domande viste in questa partita sono le seguenti: ' + str(
                active_games[game_id]['questions']))
            active_games.pop(game_id)
            ranking.pop(game_id)
            answers.pop(game_id)
            choices.pop(game_id)
            return
    bot.sendMessage(chat_id, 'Non sei admin di alcuna partita!')


def print_ranking(game_id, game_over):
    ranking_list = sorted(ranking[game_id], key=itemgetter(1), reverse=True)
    ranking_message = ''
    index = 0
    for player in ranking_list:
        if game_over:
            if index == 0:
                db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
                db.query('UPDATE app_users SET user_wins = user_wins + 1, user_games = user_games + 1 WHERE user_id = '
                         + str(player[0]) + ';')
                db.close()
            else:
                db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)
                db.query('UPDATE app_users SET user_games = user_games + 1 WHERE user_id = ' + str(player[0]) + ';')
                db.close()

        ranking_message += get_username(player[0]) + ' - ' + str(player[1]) + ' punti\n'
        index += 1
    if game_over:
        best_liar = sorted(ranking[game_id], key=itemgetter(2), reverse=True)[0]
        most_guillible = sorted(ranking[game_id], key=itemgetter(3), reverse=True)[0]
        truth_finder = sorted(ranking[game_id], key=itemgetter(4), reverse=True)[0]
        ranking_message += "\n\nIl miglior bugiardo è " + get_username(
            best_liar[0]) + ', il quale ha ingannato gli altri per ben ' + str(best_liar[2]) + ' volte!\n'
        ranking_message += "Il più credulone è " + get_username(
            most_guillible[0]) + ', il quale ha creduto a ben ' + str(most_guillible[3]) + ' bugie!\n'
        ranking_message += "Il miglior detective è " + get_username(
            truth_finder[0]) + ', il quale ha correttamente indovinato ben ' + str(truth_finder[4]) + ' fatti!\n'

    return ranking_message


def parse_message(text, chat_id, username, message_id):
    text = text.lower()
    if chat_id in active_players:
        game_id = active_players[chat_id]
        if active_games[game_id]['phase'] == 0:
            bot.sendMessage(chat_id, 'Ancora non siamo nella fase di completamento della frase, attendi.',
                            reply_to_message_id=message_id)
        elif active_games[game_id]['phase'] == 1:
            for answer in answers[game_id]:
                if chat_id in answer:
                    bot.sendMessage(chat_id, 'Hai già completato la frase! Forse volevi modificare la risposta '
                                             'con il comando /edit?', reply_to_message_id=message_id)
                    return
            for answer in answers[game_id]:
                if text in answer:
                    if answer[0] == 'correct_one':
                        bot.sendMessage(chat_id, "Sei fortunato, quella è la risposta esatta. Inseriscine"
                                                 "dunque un'altra... _ma ricordati cos'hai appena scritto!_",
                                        parse_mode='Markdown', reply_to_message_id=message_id)
                        return
                    else:
                        bot.sendMessage(chat_id, "Qualcun altro ha già inserito tale risposta! Mettine un'altra... "
                                        "_e ricordati di non farti ingannare!_", parse_mode='Markdown',
                                        reply_to_message_id=message_id)
                        return
            answers[game_id].append((chat_id, text))
            bot.sendMessage(chat_id, 'Risposta ricevuta!', reply_to_message_id=message_id)
            for player in active_games[game_id]['players']:
                if player != chat_id:
                    bot.sendMessage(player, username + ' ha risposto! Giocatori che devono ancora scegliere: ' +
                                    str(len(active_games[game_id]['players']) + 1 - len(answers[game_id])))
            if len(answers[game_id]) - 1 == len(active_games[game_id]['players']):
                active_games[game_id]['phase'] = 2
                choose_answer(game_id)
        elif active_games[game_id]['phase'] == 2:
            if not any(chat_id in choice for choice in choices[game_id]):
                if any(text in answer for answer in answers[game_id]):
                    choices[game_id].append((chat_id, text))
                    bot.sendMessage(chat_id, 'Scelta avvenuta correttamente!', reply_to_message_id=message_id)
                    for player in active_games[game_id]['players']:
                        if player != chat_id:
                            bot.sendMessage(player, username + ' ha scelto! Giocatori che devono ancora scegliere: ' +
                                            str(len(active_games[game_id]['players']) - len(choices[game_id])))
                    if len(choices[game_id]) == len(active_games[game_id]['players']):
                        active_games[game_id]['phase'] = 0
                        update_ranking(game_id)
                else:
                    bot.sendMessage(chat_id, 'Scelta non presente, fai attenzione a cosa scrivi!',
                                    reply_to_message_id=message_id)
                    return
            else:
                bot.sendMessage(chat_id, 'Hai già fornito la tua scelta!', reply_to_message_id=message_id)
                return
    else:
        bot.sendMessage(chat_id, 'Prima di poter rispondere devi partecipare o creare una partita!',
                        reply_to_message_id=message_id)


def edit_answer(text, chat_id, username, message_id):
    text = text.strip('/edit ').lower()
    if chat_id in active_players:
        game_id = active_players[chat_id]
        if active_games[game_id]['phase'] == 1:
            for answer in answers[game_id]:
                if chat_id in answer:
                    answers[game_id] = [a for a in answers[game_id] if a[0] != chat_id]
                    answers[game_id].append((chat_id, text))
                    bot.sendMessage(chat_id, 'Risposta modificata!', reply_to_message_id=message_id)
                    for player in active_games[game_id]['players']:
                        if player != chat_id:
                            bot.sendMessage(player, username + ' ha modificato la propria risposta!')
                    return
            bot.sendMessage(chat_id, 'Non hai ancora inserito una risposta, quindi perchè vorresti modificarla? Cosa '
                                     'stai nascondendo ai tuoi amici? Sei una spia del KGB? Hai mangiato tutti i '
                                     'pancake ed adesso ti senti in colpa? Riprova più tardi a modificare la tua '
                                     'risposta...', reply_to_message_id=message_id)
        else:
            bot.sendMessage(chat_id, 'In questa fase non è possibile cambiare la propria risposta.',
                            reply_to_message_id=message_id)


def select_question(chat_id, skipped):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            new_round = False
            if (len(active_games[game_id]['questions']) % 3 == 0) and (len(active_games[game_id]['questions']) != 0) \
                    and (skipped is False):
                active_games[game_id]['round'] += 1
                new_round = True
            while True:
                random_question = random.randint(1, len(questions_list))
                if (random_question not in active_games[game_id]['questions']) and \
                        (random_question not in active_games[game_id]['seen']):
                    break
            active_games[game_id]['questions'].append(random_question)
            choices[game_id] = []
            answers[game_id] = []
            answers[game_id].append(('correct_one', questions_list[random_question][1]))
            active_games[game_id]['phase'] = 1
            for player in active_games[game_id]['players']:
                if new_round:
                    message = '*Inizia un nuovo round! Round: ' + str(active_games[game_id]['round']) + '\n'
                    if active_games[game_id]['round'] == 2:
                        message += 'In questo round le bugie valgono 250 punti e la verità 1000 punti.*'
                    else:
                        message += 'In questo round le bugie valgono 500 punti e la verità 1500 punti.*'
                    bot.sendMessage(player, message, parse_mode='Markdown')
                bot.sendMessage(player, 'Ecco il prossimo fatto da riempire!\n\n' + questions_list[random_question][0])


def skip_question(chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            active_games[game_id]['seen'].append(active_games[game_id]['questions'].pop())
            choices[game_id] = []
            answers[game_id] = []
            for player in active_games[game_id]['players']:
                bot.sendMessage(player, 'Altolà, mascherina! Questa domanda è già stata vista, skippiamo...')
            select_question(chat_id, True)


def choose_answer(game_id):
    for player in active_games[game_id]['players']:
        to_send = ''
        random.shuffle(answers[game_id])
        for answer in answers[game_id]:
            to_send += str(answer[1]) + '\n'
        bot.sendMessage(player, 'Ecco le possibili risposte:\n' + to_send)


def update_ranking(game_id):
    if active_games[game_id]['round'] == 1:
        correct_answer = 500
        wrong_answer = 100
    elif active_games[game_id]['round'] == 2:
        correct_answer = 1000
        wrong_answer = 250
    elif active_games[game_id]['round'] == 3:
        correct_answer = 1500
        wrong_answer = 500
    choices_list = ''
    for choice in choices[game_id]:
        for answer in answers[game_id]:
            if choice[1] == answer[1]:
                if answer[0] != 'correct_one':
                    increase_score(answer[0], game_id, wrong_answer)
                    increase_lies(answer[0], game_id)
                    increase_fails(choice[0], game_id)
                    choices_list += get_username(choice[0]) + ' è caduto nella bugia (' + answer[1] + ') di ' + \
                        get_username(answer[0]) + ', regalandogli ' + str(wrong_answer) + ' punti!\n\n'
                else:
                    increase_score(choice[0], game_id, correct_answer)
                    increase_correct_ones(choice[0], game_id)
                    choices_list += get_username(choice[0]) + ' ha indovinato la risposta corretta (' + answer[1] + \
                        '),guadagnando ' + str(correct_answer) + ' punti!\n\n'
    for player in active_games[game_id]['players']:
        bot.sendMessage(player, choices_list)
    choices[game_id] = []
    answers[game_id] = []
    if len(active_games[game_id]['questions']) == 9:
        end_game(active_games[game_id]['admin'])


def id_add(chat_id, username):
    entry = (chat_id, username)
    if entry not in id_username:
        id_username.append(entry)


def add_player_db(chat_id, username):
    db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)

    try:
        db.query('INSERT INTO app_users (user_id, user_name, user_games, user_score, user_wins, user_lies,'
                 ' user_corrects, user_errors) VALUES (' + str(chat_id) + ', "' + username + '", 0, 0, 0, 0, 0, 0)')
    except:
        db.query('UPDATE app_users SET user_name = ' + username + ' WHERE user_id = ' + chat_id + ';')
        db.close()
        return
    db.close()


def send_stats(chat_id):
    db = _mysql.connect(host=myconf.db_host, user=myconf.db_user, passwd=myconf.db_pass, db=myconf.db_name)

    try:
        db.query('SELECT * FROM app_users WHERE user_id = ' + str(chat_id) + ';')
    except:
        bot.sendMessage(chat_id, "Devi giocare almeno una partita prima di poter vedere le tue statistiche!")
        db.close()
        return
    r = db.store_result()
    result = r.fetch_row(how=0, maxrows=1)
    bot.sendMessage(chat_id, "Your nickname: " + str(result[0][1])[2:-1] + "\n")
    db.close()


@app.route('/{}'.format(secret), methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if "message" in update:
        try:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            message_id = update["message"]["message_id"]

            try:
                username = update["message"]["from"]["username"]
                if debug:
                    bot.sendMessage(admin, '@' + username + ' (' + str(chat_id) + '): ' + update["message"]["text"])
            except KeyError:
                username = update["message"]["chat"]["first_name"]
                if debug:
                    bot.sendMessage(admin, username + ' (' + str(chat_id) + '): ' + update["message"]["text"])

            id_add(chat_id, username)

            if text == '/start':
                welcome(chat_id, username)
            elif bot_locked and (chat_id != admin):
                bot.sendMessage(chat_id, 'Il bot è attualmente bloccato e non può essere utilizzato. Contatta @Sfullez '
                                         'per chiedere di sbloccarlo.')
                bot.sendMessage(admin, username + ' ha tentato di utilizzare il bot.')
            else:
                if text == '/lock':
                    lock_bot(chat_id)
                elif text == '/create':
                    create_game(chat_id, username)
                elif text.find('/join') >= 0:
                    join_game(text, chat_id, username)
                elif text == '/start_game':
                    start_game(chat_id)
                elif text.find('/add_questions') >= 0:
                    add_questions(text, chat_id)
                elif text == '/next':
                    select_question(chat_id, False)
                elif text == '/skip':
                    skip_question(chat_id)
                elif text.find('/edit') >= 0:
                    edit_answer(text, chat_id, username, message_id)
                elif text == '/debug':
                    toggle_debug(chat_id)
                elif text == '/get_actives':
                    get_actives(chat_id)
                elif text == '/end_game':
                    end_game(chat_id)
                elif text == '/show_structures':
                    send_debug_structures(chat_id)
                elif text == '/my_stats':
                    send_stats(chat_id)
                else:
                    parse_message(text, chat_id, username, message_id)
        except KeyError:
            pass
    return "OK"
