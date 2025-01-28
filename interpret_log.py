import argparse
import csv
from typing import Any, Protocol,Iterator,Generator
import sys
import toml
from xlsxwriter.workbook import Workbook, Worksheet, Format
import xlsxwriter.exceptions as xlsx_exceptions 
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
    
    results_to_excel(logfile=log_file,
                     targetfile=output_file+".xlsx")

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
    "Gets results and creates an excel file from them."
    # CSV FORMAT

    # |               CONFIG INFO                |           Test 1          |
    # |                                          |    Site 1   |    Site 2   |   ...
    # | TEST_NUM | Test_Name | Min | Max | Units | Value | P/F | Value | P/F |
    #        ...
    # | Overall  |           |     |     |       | result| P/F | result| P/F |

    # Config # rows = 5,   Test # rows = 4,  # Columns = # tests + 4

    # Specify how to build parts in functions
    def create_config_info(ws: Worksheet,config_info:list[lf.TEST_DATA_CONFIG], first_column:int, first_row:int, 
                           f_title:Format, f_empty:Format)->None:
        "Writes config info to the Worksheet as specified in the 'CSV Format' comment in results_to_excel(). This is 5 entries long."

        ws.merge_range(first_row,first_column,first_row+1,first_column+4,"CONFIG INFO",f_title)
        ws.write_row(first_row+2,first_column,["ID","Test Name", "Min", "Max", "Units"],f_title)

        for row, requirement in enumerate(config_info, start=first_row+3):
            ws.write(row,first_column  ,requirement.test_id)
            ws.write(row,first_column+1,requirement.name)
            if requirement.min is not None:
                ws.write(row,first_column+2,requirement.min)
            else:
                ws.write(row,first_column+2,"",f_empty)
            if requirement.max is not None:
                ws.write(row,first_column+3,requirement.max)
            else:
                ws.write(row,first_column+3,"",f_empty)
            ws.write(row,first_column+4,requirement.unit)
        
        ws.merge_range(first_row+3+len(config_info),first_column,first_row+3+len(config_info),first_column+4,
                       "Overall Results:",f_title)
    
    def create_test(ws:Worksheet,test_data:list[list[lf.TEST_DATA]],test_summaries:list[lf.TEST_SUMMARY],test_name:str,first_row:int,first_column:int, f_title:Format,
                     f_pass_datapoint:Format,       f_pass_marker:Format,  f_pass_overall:Format,
                     f_fail_datapoint:Format,       f_fail_marker:Format,  f_fail_overall:Format)->None:
        "Generates a test column for the number of sites passed in in test_data, aligning to the 'Test #' part of the 'CSV Format' comment in results_to_excel(). Each test is 4 cells long."
        

        def create_site(first_row:int,first_column:int,test_data:list[lf.TEST_DATA],test_summary:lf.TEST_SUMMARY):
            "This is a 2 column long output of a single site. This pulls most of it's arguments from enclosing function."
            
            ws.merge_range(first_row,first_column,first_row,first_column+1,f"Site {test_summary.site_num}",f_title)
            ws.write_row(first_row+1,first_column,["Value","?"],f_title)

            for i, requirement in enumerate(test_data):

                datapoint_format = f_pass_datapoint if requirement.passed else f_fail_datapoint
                marker_format = f_pass_marker if requirement.passed else f_fail_marker

                ws.write(first_row+2+i,first_column,requirement.value,datapoint_format)
                ws.write(first_row+2+i,first_column+1,"P" if requirement.passed else "F",marker_format)

            overall_format = f_pass_overall if test_summary.passed else f_fail_overall
            ws.merge_range(first_row+2+len(test_data),first_column,first_row+2+len(test_data),first_column+1,
                           "P" if test_summary.passed else "F",overall_format)

        SITE_NUM_COLUMNS = 2


        ws.merge_range(first_row,first_column,first_row,first_column+3,test_name,f_title)

        #Create all sites
        for i, site_data in enumerate(test_data):
            create_site(first_row=      first_row+1,
                        first_column=   first_column+(i*SITE_NUM_COLUMNS),
                        test_data=      site_data,
                        test_summary=   test_summaries[i])
            
    def create_tests(ws:Worksheet,test_data:list[list[lf.TEST_DATA]],test_summaries:list[lf.TEST_SUMMARY],site_count:int,first_row:int,first_column:int, f_title:Format,
                     f_pass_datapoint:Format,       f_pass_marker:Format,  f_pass_overall:Format,
                     f_fail_datapoint:Format,       f_fail_marker:Format,  f_fail_overall:Format)->None:
        "Generates all of the tests for datapoints Filling in the tests... part of the 'CSV Format' comment in results_to_excel(). Each test is 4 cells long."
        
        TEST_NUM_COLUMNS = 4

        test_count = int(len(test_data)/site_count)

        for test in range(test_count):
            create_test(ws=ws,
                        test_data=test_data             [ test*site_count : (test+1)*site_count ],
                        test_summaries=test_summaries   [ test*site_count : (test+1)*site_count ],
                        test_name=f"TEST #{test+1}",
                        first_row=first_row,
                        first_column=first_column+(test*TEST_NUM_COLUMNS),
                        f_title=f_title,
                        f_pass_datapoint=f_pass_datapoint, f_pass_marker=f_pass_marker, f_pass_overall=f_pass_overall,
                        f_fail_datapoint=f_fail_datapoint, f_fail_marker=f_fail_marker, f_fail_overall=f_fail_overall)

    def create_requirement_report(ws:Worksheet,requirement:lf.TEST_DATA_CONFIG,requirement_data:list[lf.TEST_DATA],summaries:list[lf.TEST_SUMMARY],
                                  site_count:int,first_row:int,first_column:int, f_title:Format, 
                                  f_pass_datapoint:Format,       f_pass_marker:Format,
                                  f_fail_datapoint:Format,       f_fail_marker:Format)-> None:
        
        ws.write_row(first_row,first_column,["ID","Test Name", "Min", "Max", "Units"],f_title)
        
        # Write second row (copied from create_config_info)
        row = first_row + 1
        ws.write(row,first_column  ,requirement.test_id)
        ws.write(row,first_column+1,requirement.name)
        if requirement.min is not None:
            ws.write(row,first_column+2,requirement.min)
        else:
            ws.write(row,first_column+2,"",f_empty)
        if requirement.max is not None:
            ws.write(row,first_column+3,requirement.max)
        else:
            ws.write(row,first_column+3,"",f_empty)
        ws.write(row,first_column+4,requirement.unit)

        # skip a column and start writing out results in the following roles
        column = first_column + 6
        ws.write_column(first_row,column,[f"T{(i//site_count)+1}-S{(s.site_num)}" for i,s in enumerate(summaries)])
        for i,data in enumerate(requirement_data):
            f_datapoint = f_pass_datapoint if data.passed else f_fail_datapoint
            f_marker = f_pass_marker if data.passed else f_fail_marker
            ws.write(i,column,f"T{(i//site_count)+1}-S{(summaries[i].site_num)}",f_datapoint)
            ws.write(i,column+1,"P" if data.passed else "F",f_marker)
            ws.write(i,column+2,data.value,f_datapoint)


    test_config_rows, test_data, test_summaries = lf.get_test_results_from_logfile(logfile)

    #Calculating some useful values
    site_test_count = len(test_summaries) # each site counts as one test
    site_count = len(set([ s.site_num for s in test_summaries])) # Collects all site numbers and finds the number of distinct sites, assumes site used in each test

    requirement_count = len(test_config_rows) # Each of the things that will be tested.

    try:
        with Workbook(targetfile) as wb:
            all_results = wb.add_worksheet(name="Overall Results")

            # Get formats
            f_none          = format_from_config(wb,"none")
            f_pass          = format_from_config(wb,"pass")
            f_subtle_pass   = format_from_config(wb,"subtle_pass")
            f_fail          = format_from_config(wb,"fail")
            f_subtle_fail   = format_from_config(wb,"subtle_fail")
            f_empty         = format_from_config(wb,"empty")
            f_title         = format_from_config(wb,"title")

            # Create main results file
            create_config_info(all_results,test_config_rows,0,0,
                            f_title=f_title,f_empty=f_empty)

            create_tests(all_results,test_data,test_summaries,site_count,0,5,f_title=f_title,
                        f_pass_datapoint=f_none,        f_pass_marker=f_pass,  f_pass_overall=f_pass,
                        f_fail_datapoint=f_subtle_fail, f_fail_marker=f_fail,  f_fail_overall=f_fail)
            
            all_results.autofit()

            # Create results file for each requirement
            for r in range(requirement_count):
                req_results = wb.add_worksheet(name=f"{test_config_rows[r].test_id}-{test_config_rows[r].name}")
                create_requirement_report(ws= req_results,
                                          requirement=test_config_rows[r],
                                          requirement_data=[d[r] for d in test_data],
                                          summaries=test_summaries,
                                          site_count=site_count,
                                          first_row= 0, 
                                          first_column=0,
                                          f_title= f_title,
                                          f_pass_datapoint=f_subtle_pass, f_pass_marker=f_pass,
                                          f_fail_datapoint=f_subtle_fail, f_fail_marker=f_fail
                                          )
                req_results.autofit()

                

    except (PermissionError,xlsx_exceptions.FileCreateError) as e:
        raise type(e)(str(e) + f" You may have this file open in another program.'").with_traceback(sys.exc_info()[2])
                    #https://stackoverflow.com/questions/6062576/adding-information-to-an-exception


if __name__ == "__main__":
    run()