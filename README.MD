# Devman underground chat client

GUI to the secret underground chat. It is working with socket connection. This project created for study proposes. It is
a part of [dvmn.org](https://dvmn.org/modules/async-python) async python course.

### Prerequisites

This script was developed using  `python == 3.8`

Have installed:

* [git](https://git-scm.com/)
* [pyenv](https://github.com/pyenv/pyenv)
* [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)

### Installing

Prepare execution environment

```bash
git clone git@github.com:rkinwork/dvmn-anonymous-chat-client.git
pyenv install 3.8.2
cd dvmn-anonymous-chat-client
pyenv virtualenv 3.8.2 dvmn-anonymous-chat-client
pyenv activate dvmn-anonymous-chat-client
```

Install dependencies

```bash
pip3 install -r requirements.txt
```

### First use. Register

Run

```bash
python main.py -n
```

### Launch program

Run

```bash
python main.py -t xxxxSECRETTOKENxxxxx
```

### Settings

To see all available setting

```bash
python main.py -h
```

For example, you can switch on debug mode, redefine connection setting or set new filepath for history file. All you can do via cli arguments, ENV
variables or creating `conf.ini` file in the project root

|Action|Option| Env variable|
|---|---|---|
|Show help|-h||
|History log| -f --filepath| DVMN_CHAT_PATH|
|Host| -u --host| DVMN_HOST|
|Send port| -p --port| DVMN_SEND_PORT|
|Listen port| -l --lport| DVMN_PORT|
|Set token| -t --token| DVMN_AUTH_TOKEN|
|Register new user| -n --register| |
|Switch on debug mode| -d --debug||

##TROUBLESHOOTING 

### Problems with connection
Contact with server admins via [Telegram group](tg://resolve?domain=dvmn_flood)

### Tkinter on Mac
There some problems with first launching on MacOS - I this is useful [question](https://stackoverflow.com/questions/42345189/how-to-use-the-tkinter-module-on-macossierra)

## Authors

* **Roman Kazakov**
* **DVMN.ORG team**

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

