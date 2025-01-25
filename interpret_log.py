import argparse
import csv
from typing import Any, Protocol,Iterator,Generator
import sys
import toml
from xlsxwriter.workbook import Workbook, Worksheet, Format
import src.logfile_reading as lf
from src.excel_writing import format_from_config

pyproj_conf = toml.load("./pyproject.toml")

# To Add Better Formatting, see these articles explaining exporting directly to xlsx file:
# https://techsorber.com/how-to-merge-cells-in-excel-using-python-pandas/
# https://stackoverflow.com/questions/61217923/merge-rows-based-on-value-pandas-to-excel-xlsxwriter
# https://xlsxwriter.readthedocs.io/example_merge1.html
# https://pythonbasics.org/write-excel/

#Extract desired information from pyproject.toml
authors = pyproj_conf["tool"]["poetry"]["authors"]

program_name = "Interpret Log Files"
program_description = "Turns the Log Files (.log) of test results into a convenient table (.csv). (Note that the .log file is a specific .csv.)"+\
                        "This is designed to interpret the output of Eagle's ETS-364B tester."
program_epilog = f"Author{'s' if len(authors) else ''}: {', '.join([a for a in authors])}"

#Default Values:
DEFAULT_OUTPUT_NAME = "output"

# Remove referances to allow to be deleted after extracted desired values
del authors
del pyproj_conf

parser = argparse.ArgumentParser(prog=program_name,
                                 description=program_description,
                                 epilog=program_epilog)
parser.add_argument('-l','--log',type=str,default=None,
                   help=f"The file ")
parser.add_argument('-o','--output',type=str,default=DEFAULT_OUTPUT_NAME,
                    help= f"The path of the .csv file and .xlsx that this program should output. Default: {DEFAULT_OUTPUT_NAME}.csv & .xlsx")

def run():
    "Only run parser if directly called."
    args = parser.parse_args()
    log_file = args.log
    output_file = args.output

    if log_file is None:
        raise ValueError("No logfile was provided")
    
    results_to_csv(logfile=log_file,
                    targetfile=output_file+".csv")
    
    #results_to_excel(logfile=log_file,
    #                 targetfile=output_file+".xlsx")

def results_to_csv(logfile: str, targetfile: str) -> None:
    "This takes the logfile and generates a csv outpu in the target file."

    test_config_rows, test_data, test_summaries = lf.get_test_results_from_logfile(logfile)
    
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
                cfg:lf.TEST_DATA_CONFIG = test_config_rows[r]
                row = [cfg.test_id,
                    cfg.name,
                    cfg.min if not None else '',
                    cfg.max if not None else '',
                    cfg.unit]
                for t in range(site_test_count):
                    data:lf.TEST_DATA = test_data[t][r]
                    row += [data.value,lf.passed_to_pass_fail(data.passed)]
                csvwriter.writerow(row)

            # Write Final summary Row
            row = "Overall,,,,".split(",")
            for i in range(site_test_count):
                row += ['',lf.passed_to_pass_fail(test_summaries[i].passed)]
            csvwriter.writerow(row)

    except PermissionError as e:
        raise type(e)(str(e) + f"You may have this file open in another program.'").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception

def results_to_excel(logfile:str, targetfile:str):
    test_config_rows, test_data, test_summaries = lf.get_test_results_from_logfile(logfile)
    
    # CSV FORMAT

    # |               CONFIG INFO                |           Test 1          |
    # |                                          |    Site 1   |    Site 2   |   ...
    # | TEST_NUM | Test_Name | Min | Max | Units | Value | P/F | Value | P/F |
    #        ...
    # | Overall  |           |     |     |       | result| P/F | result| P/F |

    # Config # rows = 5,   Test # rows = 4,  # Columns = # tests + 4

    # Specify how to build parts in functions
    def create_config_info(ws: Worksheet,config_info:list[lf.TEST_DATA_CONFIG], first_column:int, first_row:int ,format_empty_cells:bool, f_empty:Format):
        "Writes config info to the Worksheet as specified in the 'CSV Format' comment in results_to_excel(). This is 5 entries long."
        c = first_column
        r = first_row

        ws.merge_range(r,c,r,c+4,"CONFIG INFO")



    #Calculating some useful values
    site_test_count = len(test_summaries) # each site counts as one test
    site_count = len(set([ s.site_num for s in test_summaries])) # Collects all site numbers and finds the number of distinct sites, assumes site used in each test
    test_count = int(site_test_count/site_count)

    requirement_count = len(test_config_rows) # Each of the things that will be tested.

    with Workbook(targetfile) as wb:
        all_results = wb.add_worksheet(name="Results")

        # Get formats
        f_pass = format_from_config(wb,"pass")
        f_subtle_pass = format_from_config(wb,"subtle_pass")
        f_fail = format_from_config(wb,"fail")
        f_subtle_fail = format_from_config(wb,"subtle_fail")
        f_empty = format_from_config(wb,"empty")

    


        


if __name__ == "__main__":
    run()