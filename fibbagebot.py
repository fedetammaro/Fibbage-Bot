from flask import Flask, request
import urllib3
import telepot
import pickle
import random
import questions

proxy_url = "http://proxy.server:3128"
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
answers = {}
broadcast_list = []
admin = YOUR_TELEGRAM_ID
debug = False

secret = YOUR_SECRET
bot = telepot.Bot(YOUR_TELEGRAM_BOT_ID)
bot.setWebhook(
    LINK_TO_YOUR_PYTHONANYWHERE.format(secret),
    max_connections=1)
app = Flask(__name__)

bot.sendMessage(admin, "Bot started!")


def parse_update(update):
    return update["message"]["text"], update["message"]["chat"]["id"], update["message"]["from"]["first_name"]
    # testo, id, nome


def welcome(update):
    bot.sendMessage(parse_update(update)[1],
                    "Questo bot ti permette di giocare a Fibbage assieme ai tuoi amici, meglio se dal vivo. "
                    "Scrivi /start_game per iniziare una nuova partita, oppure /join_game [id] per entrare in un match."
                    " Nel caso tu voglia suggerire una domanda (compresa di risposta, grazie!) scrivi /suggest [domanda]"
                    " [risposta], e il mio creatore potrebbe aggiungerla alla lista!")


def toggleDebug(chat_id):
    global debug
    if chat_id == admin:
        debug = not debug
        bot.sendMessage(chat_id, "Debug: " + str(debug))
    else:
        bot.sendMessage(chat_id, "You're not allowed to toggle debug.")


def broadcast(chat_id):
    if chat_id == admin:
        bot.sendMessage(chat_id, broadcast_list)
    else:
        bot.sendMessage(chat_id, "You're not allowed to see the broadcast list.")


def get_actives(chat_id):
    if chat_id == admin:
        bot.sendMessage(chat_id, active_players)
    else:
        bot.sendMessage(chat_id, "You're not allowed to see the active players list.")


def broadcast_add(user_details):
    if user_details not in broadcast_list:
        broadcast_list.append(user_details)


def create_game(chat_id, username):
    game_id = random.randint(1,1001)
    if chat_id in active_players:
        bot.sendMessage(chat_id, 'Sei già in una partita!')
    else:
        active_games[game_id] = {'admin': chat_id, 'players': [chat_id], 'usernames': [username], 'running': False}
        active_players[chat_id] = game_id
        bot.sendMessage(chat_id, 'Hai creato la partita con ID ' + str(game_id) +'. Passa tale ID agli altri giocatori!')


def start_game(chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            active_games[game_id]['running'] = True
            for player in active_games[game_id]['players']:
                bot.sendMessage(player, 'La partita è iniziata!')


def game():
    pass


def join_game(text, chat_id, username):
    game_id = text.strip('/join_game ')
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
                    bot.sendMessage(chat_id, 'Giocatori attualmente in partita: ' + player_list[0:(len(player_list) - 2)])
            else:
                bot.sendMessage(chat_id, 'Non esiste alcuna partita con ID ' + str(game_id) + '!')
    except ValueError:
        bot.sendMessage(chat_id, 'Inserire un ID valido dopo /join_game!')


def end_game(text, chat_id):
    for game_id in active_games:
        if active_games[game_id]['admin'] == chat_id:
            for player in active_games[game_id]['players']:
                bot.sendMessage(player, 'La partita con ID ' + str(game_id) + ' è terminata!')
                active_players.pop(player)
            active_games.pop(game_id)
            return
    bot.sendMessage(chat_id, 'Non sei admin di alcuna partita!')


def parse_message(text, chat_id, username):
    if (chat_id in active_players) and (chat_id not in answers):
        game_id = active_players.get(chat_id)
        if active_games[game_id]['running']:
            answers[chat_id] = text
            bot.sendMessage(chat_id, 'Risposta ricevuta!')
            if chat_id != active_games[game_id]['admin']:
                bot.sendMessage(active_games[game_id]['admin'], username + ' ha risposto!')


@app.route('/{}'.format(secret), methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if "message" in update:
        try:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]

            try:
                username = update["message"]["from"]["username"]
            except KeyError:
                username = update["message"]["chat"]["first_name"]

            broadcast_add([username, chat_id])

            if debug:
                bot.sendMessage(admin, '@' + username + ' (' + str(chat_id) + '): ' + update["message"]["text"])

            if text == '/start':
                welcome(update)
            elif text == '/create_game':
                create_game(chat_id, username)
            elif text.find('/join_game') >= 0:
                join_game(text, chat_id, username)
            elif text == '/start_game':
                start_game(chat_id)
            elif text == '/debug':
                toggleDebug(chat_id)
            elif text == '/broadcast':
                broadcast(chat_id)
            elif text == '/get_actives':
                get_actives(chat_id)
            elif text.find('/end_game') >= 0:
                end_game(text, chat_id)
            else:
                parse_message(text, chat_id, username)
        except KeyError:
            pass
    return "OK"
