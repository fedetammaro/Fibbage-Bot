# Bot di Fibbage per Telegram
È possibile utilizzare questo bot di Telegram per giocare a Fibbage coi propri amici tramite Telegram; è possibile provare il bot [nella versione che ho hostato su PythonAnywhere](https://t.me/fibbagebot).
Il bot è stato creato utilizzando Python 3.6 ed utilizza dei webhook per ricevere i messaggi tramite le API di Telegram girando su PythonAnywhere.

#### Lista di dipendenze per poter utilizzare il bot
* Telepot per le API di Telegram - [link](https://github.com/nickoala/telepot)
* Flask, urllib3 per i webhook

#### Requisiti aggiuntivi
La lista di domande che utilizzo nel mio bot è stata rimossa in quanto contiene tutte le risposte ed è stata tradotta in italiano dalla sua versione inglese (il bot è completamente in italiano). Ogni domanda è stata trascritta a mano e modificata dalle due versioni di Fibbage contenute nei primi due Jackbox Party Pack. Dunque, affinchè sia possibile utilizzare questo bot nel caso qualcuno lo voglia hostare in una sua piattaforma, è necessario un file nominato "questions.py" contenente una lista nominata "question_list" nel seguente formato:
```python
questions_list = [("Ecco una domanda", "Risposta corretta alla domanda"), ("Ecco una seconda domanda", "Risposta corretta alla domanda")]
```

#### Come utilizzare il bot
È possibile creare una partita tramite il comando */create*, il quale crea la partita e assegna un ID affinchè gli altri giocatori possano unirsi tramite il comando */join* seguito dall'ID della partita.
Una volta che tutti i partecipanti si sono uniti, si può far partire il gioco tramite il comando */start_game*. Da quel momento tutto si svolge secondo le dinamiche del gioco, che prevedono che ciascuna domanda sia ottenuta tramite il comando */next*.
Si può interrompere la partita in qualsiasi momento tramite il comando */end_game* oppure la partita termina normalmente alla fine del terzo round (dopo 9 domande). I giocatori possono modificare la risposta che hanno inserito tramite il comando */edit*.

---

# Fibbage Telegram Bot
Use this Telegram bot to play with your friends through Telegram; you can try [the one I hosted on PythonAnywhere](https://t.me/fibbagebot).
The bot has been created using Python 3.6 and uses webhooks to receive messages through the Telegram API, while running on PythonAnywhere.

#### List of dependencies
* Telepot for Telegram API - [link](https://github.com/nickoala/telepot)
* Flask, urllib3 for webhooks

#### Additional setup
The questions list I use in my bot has been removed, since it contains all the answers and has been translated to Italian (the bot is entirely in Italian). Every question has been copied by hand and modified from the two Fibbage game included in the Jackbox Party Pack. So, in order to make this bot run, you'll need a "questions.py" file containing a "questions_list" list like this:
```python
questions_list = [("Here's the question", "Correct answer"), ("Second question", "Correct answer")]
```
