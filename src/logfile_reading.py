from enum import Enum
from dataclasses import dataclass
from typing import Any, Protocol, Generator, Iterator
import csv 
import sys

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
    "Boolean passed -> 'T'/'F'"
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
    "Turns a row of the CSV into its associated dataclass."
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

def interpreted_logfile(log_file_path: str) -> Generator[LOG_ROW, None,None]:
    "This returns a generator that returns the dataclasses from interpreting rows of the logfile as they are needed."
    with open(log_file_path,mode="r",newline="\n") as csvfile:
        logreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row_num,row in enumerate(logreader):
            try:
                yield row_list_to_dataclass(list(row))
            except Exception as e:
                raise type(e)(str(e) + f"Occoured in line {row_num} of the logfile provided '{log_file_path}'").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception

def get_test_results_from_logfile(logfile:str) -> tuple[list[TEST_DATA_CONFIG],list[list[TEST_DATA]],list[TEST_SUMMARY]]:
    """interprets log file and outputs the (config_rows, data, summaries) from all of the tests.
        |-> config_rows:    List of all config rows, in logfile order, specify tests by id
        |-> test_data:      List of lists of config data, inner list in same order as test_config_rows, outer in same order as test_summaries
        |-> test_summaries: List all summaries in the order they are presented in logfile
        *** This is a non-ideal solution, but it works, so it is not a problem. ***
    """
    
    # Extract all test data
    test_config_rows:   list[TEST_DATA_CONFIG]  =[] # list of all config rows, in logfile order, specify tests by id
    test_data:          list[list[TEST_DATA]]   =[] #List of lists of config data, inner list in same order as test_config_rows, outer in same order as test_summaries
    test_summaries:     list[TEST_SUMMARY]      =[] # List all summaries in the order they are presented in logfile

    processing_data = False # Flag notes when currently in a TEST_DATA section

    # Extract test results from logfile
    for log_row in interpreted_logfile(logfile):

        match log_row.type:

            case Row_Types.TEST_DATA_CONFIG:
                test_config_rows.append(log_row)

            case Row_Types.TEST_SUMMARY:
                test_summaries.append(log_row)
                processing_data = False # Rows happen whenever exit TEST_DATA section

            case Row_Types.TEST_DATA:
                if processing_data:
                    test_data[-1].append(log_row)
                else:
                    test_data.append([log_row])
                    processing_data = True # Have started brocessing block of data
            
            case _:
                pass
    
    return (test_config_rows,test_data,test_summaries)

