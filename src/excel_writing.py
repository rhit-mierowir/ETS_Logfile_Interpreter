import toml
import sys
from xlsxwriter.workbook import Workbook, Format

CONFIG_FILEPATH = "./config.toml"

config_data = toml.load(CONFIG_FILEPATH)

# Make variables that can be called in code to get formatting info
formats = config_data["format"]

conditional_formats = config_data["format"]["conditional"]

def format_from_config(wb:Workbook, config_format_name=str)->Format:
    "returns a formatting object following the specification in config.toml (e.g. config: [format.pass] -> config_format_name='pass')"
    try:
        return wb.add_format(formats[config_format_name])
    except KeyError as e:
        raise type(e)(str(e) + f"\nCould not find [format.{config_format_name}] in the config file ({CONFIG_FILEPATH})").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception

def conditional_format_from_config(wb:Workbook,config_format_name=str)->Format:
    raise NotImplementedError()