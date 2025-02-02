# REST-RCE

A REST interface for the orchestration software RCE designed by DLR.
Integrate discipline-specific research software tools in RCE using a REST interface.

- ✨ Easily interact with complex RCE tools via REST API
- 💬 Define configurations using a simple JSON interface
- 🤖 Automate execution and manage error handling seamlessly
- 💻 Execute RCE workflows in parallel, improving efficiency
- 🔍 Monitor and log errors for better diagnosis and troubleshooting
- 🚀 Scale your RCE tool usage with parallel requests

## 🔨 Installation & Setup 
1. Install [Python 3.11](README.md#python)
2. Install [poetry](README.md#poetry) 
3. Install dependencies using poetry
4. Select new poetry environment
5. Install [pre-commit](README.md#pre-commit) hooks

## 💡 Usage
REST-RCE can be used via a command line interface.
As long as you are somewhere in the project's directory, the tool can be run via:

    poetry run rest_rce <path_to_config_file>

After this command, the REST-RCE server will be started and the configuration file will be loaded.  
The server will listen for incoming post requests at http://127.0.0.1:8000/execute-tool/ and execute the tool as 
defined in the configuration file with the input parameters given in the request.  
To make this command work, make sure that you have [poetry](README.md#poetry) and the projects dependencies installed.

### 🔧 Parameters

REST-RCE can be run with various different parameters. To check the options in the command line run:

    poetry run rest_rce --help

#### Required parameters: 
- 'config_file_path': 
  - type=str
  - Relative or absolute path to the configuration file of the tool that you want to execute using 
  REST-RCE. 
  - Can be passed without explicitly writing 'config_file_path' before the input.

#### Optional parameters: 
- '-t' or '--timeout':
  - type=float
  - Time after which the command script should terminate if it did not execute successfully already. 
  - default=None

- '-r', '--request_limit': 
  - type=int
  - Request limit for parallel processes. If it is reached, further post requests will be denied.
  - default=10

## ❓ Detailed setup information 

### Python
This project uses Python 3.11

1. Download and install Python 3.11 from [here](https://www.python.org/downloads/)
> Environment variables get set during the installation, activate `Add Python 3.11 to PATH`
2. Restart your computer
3. You are finished 🎉

### Poetry
This project uses poetry for dependency management. 
1. First up, download and install poetry. Either go to the official [documentation](https://python-poetry.org/) or run the following commands

**Powershell**

    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

**Bash**

    curl -sSL https://install.python-poetry.org | python3 -

Check whether poetry was correctly installed and added to your path. Use poetry version >= 1.5.0.

**Powershell/Bash**

    poetry --version

2. In your terminal, navigate into Software_Quality and run `poetry install`. 
This will create a new virtual environment and install the dependencies defined in the `poetry.lock` file.
3. If you want to contribute to the project run `poetry install --with dev` to install the development dependencies.
4. In your IDE, select the new virtual environment.
5. You are finished 🎉

### Pre-commit
This project uses [pre-commit](https://pre-commit.com) hooks for code linting and formatting using 
[Ruff](https://docs.astral.sh/ruff/).

1. Download the dependencies from the 'dev' dependency group using poetry.
2. Install the git hook scripts defined in the [configuration file](.pre-commit-config.yaml).

**Powershell/Bash**

    pre-commit install

3. Run the hooks against all the files to check if they work. 

**Powershell/Bash**

    pre-commit run --all-files

4. You are finished 🎉 from now on all staged Python files will be linted and formatted at every commit.
