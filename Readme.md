# RecordTreeDownloader

This tool imports `Record Tree` file into a SQLite database and automates file downloads using MEGA CMD

## Prerequisties

Before running the application, ensure you have the fillowing installed:

- [Python](https://www.python.org/downloads/) (Developed and tested on v3.13.1)
- [MEGA CMD](https://mega.io/cmd)

## Installation

Install the required Python libraries using pip:

```bash
pip install -r requirements.txt
```

## configuration

Update the configuration values in `config.py` to match your local environment and choose a run mode

## Usage

Once configured, start the app by running:

```bash
python main.py
```

## Other

- `record.py`: This is a legacy file used during the initial development phase and currently serves no functional purpose in the main workflow
