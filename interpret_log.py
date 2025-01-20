import argparse
from enum import Enum
import csv 
from dataclasses import dataclass
from typing import Any, Protocol
import sys
import toml

pyproj_conf = toml.load("./pyproject.toml")

#Extract desired information from pyproject.toml
authors = pyproj_conf["tool"]["poetry"]["authors"]

program_name = "Interpret Log Files"
program_description = "Turns the Log Files (.log) of test results into a convenient table (.csv). (Note that the .log file is a specific .csv.)"+\
                        "This is designed to interpret the output of Eagle's ETS-364B tester."
program_epilog = f"Author{'s' if len(authors) else ''}: {', '.join([a for a in authors])}"

#Default Values:
DEFAULT_OUTPUT_PATH = "output.csv"

# Remove referances to allow to be deleted after extracted desired values
del authors
del pyproj_conf

parser = argparse.ArgumentParser(prog=program_name,
                                 description=program_description,
                                 epilog=program_epilog)
parser.add_argument('-l','--log',type=str,default=None,
                   help=f"The file ")
parser.add_argument('-o','--output',type=str,default=DEFAULT_OUTPUT_PATH,
                    help= f"The path of the .csv file that this program should output. Default: {DEFAULT_OUTPUT_PATH}")

class Row_Types(Enum):
    TEST_DATA_CONFIG    = 10
    TEST_DATA           = 100
    TEST_SUMMARY        = 130
    WARNING             = 145
    HEADER              = 120
    HEADER2             = 125
    FILE_INFO           = 140
    UNKNOWN             = -1

def row_number_to_row_types(row_number:int)->Row_Types:
    try:
        return Row_Types._value2member_map_[row_number]
    except KeyError:
        print(f"Unknown row type found: number {row_number}")
        return Row_Types.UNKNOWN


class LOG_ROW(Protocol):
    type: Row_Types

@dataclass
class UNSPECIFIED_LOG_ROW:
    type: Row_Types
    data: list[Any]

@dataclass
class TEST_DATA_CONFIG:
    test_id: str
    decimal_position: int #Assumed, not sure
    min: float|None
    max: float|None
    unit:str
    name:str
    type: Row_Types = Row_Types.TEST_DATA_CONFIG

@dataclass
class TEST_DATA:
    test_id: str
    issue: str
    passed: bool
    value: float
    type: Row_Types = Row_Types.TEST_DATA

@dataclass
class TEST_SUMMARY:
    site_num: int
    time_completed: str
    serial_num:str
    passed:bool
    unknown1:Any
    unknown2:Any
    bin_num:int
    unknown3:Any
    unknown4:Any

    type: Row_Types = Row_Types.TEST_SUMMARY

def pass_fail_to_passed(pf:str)->bool:
    "turn p->true and f->fail, default to fail if can't tell"
    match pf.lower():
        case "p":
            return True
        case "f":
            return False
        case _:
            return False

def passed_to_pass_fail(passed:bool)->str:
    if passed:
        return "P"
    else:
        return "F"

def convert_data_to_float(data:str)->float|None:
    try:
        return float(data)
    except ValueError:
        return None

    
def row_list_to_dataclass(row_list:list[str])->LOG_ROW:
    type:Row_Types = row_number_to_row_types(int(row_list[0]))
    match type:
        case Row_Types.TEST_DATA_CONFIG:
            return TEST_DATA_CONFIG(
                                    test_id=            row_list[1],
                                    decimal_position=   int(row_list[2]),
                                    min=                convert_data_to_float(row_list[3]),
                                    max=                convert_data_to_float(row_list[4]),
                                    unit=               row_list[5],
                                    name=               row_list[6]
                                    )
        case Row_Types.TEST_DATA:
            return TEST_DATA(
                             test_id=   row_list[1],
                             issue=     row_list[2],
                             passed=    pass_fail_to_passed(row_list[3]),
                             value=     float(row_list[4])
                             )
        case Row_Types.TEST_SUMMARY:
            return TEST_SUMMARY(
                                site_num=       int(row_list[1]),
                                time_completed= row_list[2],
                                serial_num=     row_list[3],
                                passed=         pass_fail_to_passed(row_list[4]),
                                unknown1=       row_list[5],
                                unknown2=       row_list[6],
                                bin_num=        int(row_list[7]),
                                unknown3=       row_list[8],
                                unknown4=       row_list[9])
        case _:
            return UNSPECIFIED_LOG_ROW(type,row_list.copy()[1:])

def run():
    "Only run parser if directly called."
    args = parser.parse_args()
    log_file = args.log
    output_file = args.output

    if log_file is None:
        raise ValueError("No logfile was provided")
    
    get_log_results(logfile=log_file,
                    targetfile=output_file)

def get_log_results(logfile: str, targetfile: str):
    "This takes the logfile and generates a csv outpu in the target file."

    # Extract all test data
    test_config_rows:   list[TEST_DATA_CONFIG]  =[] # list of all config rows, in logfile order, specify tests by id
    test_data:          list[list[TEST_DATA]]   =[] #List of lists of config data, inner list in same order as test_config_rows, outer in same order as test_summaries
    test_summaries:     list[TEST_SUMMARY]      =[] # List all summaries in the order they are presented in logfile

    processing_data = False # Flag notes when currently in a TEST_DATA section

    # Extract test results from logfile
    with open(logfile,mode="r",newline="\n") as csvfile:
        logreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row_num,row in enumerate(logreader):
            try:
                row_interpreted = row_list_to_dataclass(list(row))
            except Exception as e:
                raise type(e)(str(e) + f"Occoured in line {row_num} of the logfile provided '{logfile}'").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception
            match row_interpreted.type:

                case Row_Types.TEST_DATA_CONFIG:
                    test_config_rows.append(row_interpreted)

                case Row_Types.TEST_SUMMARY:
                    test_summaries.append(row_interpreted)
                    processing_data = False # Rows happen whenever exit TEST_DATA section

                case Row_Types.TEST_DATA:
                    if processing_data:
                        test_data[-1].append(row_interpreted)
                    else:
                        test_data.append([row_interpreted])
                        processing_data = True # Have started brocessing block of data
                
                case _:
                    pass
    

    # CSV FORMAT
    # |               CONFIG INFO                |           Test 1          |
    # |                                          |    Site 1   |    Site 2   |   ...
    # | TEST_NUM | Test_Name | Min | Max | Units | Value | P/F | Value | P/F |
    #        ...
    # | Overall  |           |     |     |       | result| P/F | result| P/F |

    # Config # rows = 5,   Test # rows = 4,  # Columns = # tests + 4

    # Write results to new csv file
    site_test_count = len(test_summaries) # each site counts as one test
    site_count = len(set([ s.site_num for s in test_summaries])) # Collects all site numbers and finds the number of distinct sites, assumes site used in each test
    test_count = int(site_test_count/site_count)

    testcase_rows = len(test_config_rows)

    assert test_count == int(test_count), "Make sure it and site_count is an integer"
    
    try:
        with open(targetfile, mode="w",newline="\n") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # Make Top Level Headers
            row =  "Config Information,,,,".split(",")
            for num in range(test_count):
                row += [f"Test #{num+1}",''] + (["",""]*(site_count-1))
            csvwriter.writerow(row)

            # Make Second Level Headers
            row = ",,,,".split(",")
            for i in range(site_test_count):
                    row += f"Site {test_summaries[i].site_num},".split(",")
            csvwriter.writerow(row)

            # Make Third Level Headers
            row = "#,Name,Min,Max,Unit".split(",")
            for _ in range(test_count):
                for _ in range(site_count):
                    row += "Value,?".split(",")
            csvwriter.writerow(row)

            # Write rows for all data rows
            for r in range(testcase_rows):
                cfg:TEST_DATA_CONFIG = test_config_rows[r]
                row = [cfg.test_id,
                    cfg.name,
                    cfg.min if not None else '',
                    cfg.max if not None else '',
                    cfg.unit]
                for t in range(site_test_count):
                    data:TEST_DATA = test_data[t][r]
                    row += [data.value,passed_to_pass_fail(data.passed)]
                csvwriter.writerow(row)

            # Write Final summary Row
            row = "Overall,,,,".split(",")
            for i in range(site_test_count):
                row += ['',passed_to_pass_fail(test_summaries[i].passed)]
            csvwriter.writerow(row)

    except PermissionError as e:
        raise type(e)(str(e) + f"You may have this file open in another program.'").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception

if __name__ == "__main__":
    run()