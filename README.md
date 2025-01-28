# ETS_Logfile_Interpreter
A python program to interpret the log files of a ETS-364B (Eagle Test Systems) IC tester, but probably generalizes.

## Installation

git clone this repository

## Install Poetry
To manage dependancies for this python project, we are using [Poetry](https://python-poetry.org/docs/), which automatically handles dependancies and conflicts with other python versions and dependancies by running all code in separate virtual environments. Poetry is configured in the pyproject.toml file.

### Install directly from poetry
Alternatively, you could [Install Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) by directly downloading the official installer.

Windows (Powershell)
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

Linux, MacOs, Windows WSL
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Install with Pipx
Install [Pipx](https://pipx.pypa.io/stable/installation/)

(On Windows, using Powershell, also installing [scoop](https://scoop.sh/))
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
scoop install pipx
pipx ensurepath
```
> There is a way to install pipx using pip, see "Install via pip (requires pip 19.0 or later)" on the pipx website linked above.

Install [Poetry](https://python-poetry.org/docs/)
```bash
pipx install poetry
```

## Install Dependancies for Python Program
```bash
cd <path/of/this/repository>
poetry install
```
- `cd <path/of/this/repository>` : change directory into the folder you downloaded this repository to

## Run Script
```bash
cd <path/of/this/repository>
poetry run ./interpret_log.py -l <logfile> -o <outputfile>
```
- `cd <path/of/this/repository>` : change directory into the folder you downloaded this repository to
- `<logfile>` : The logfile (.log) you want to interpret
- `<outputfile>` : The path you want to generate the outputfile (.csv)

## Help
```bash
poetry run ./interpret_log.py -h
```
- This prints out the help output including information about all the arguments you can pass into it on the command line.