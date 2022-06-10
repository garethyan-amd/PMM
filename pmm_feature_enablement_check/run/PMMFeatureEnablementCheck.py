#!/usr/bin/python3
import CommonWorkloadHelper
import collections
import Defaults
import pickle
import sys
import csv
import os
import argparse
import re
import pathlib
import shutil
from papi2 import *

REGISTER=Defaults.createMultDict()
TAGSETTING=Defaults.createMultDict()
FEATUREBITS=Defaults.createMultDict()
FEATURESTATUS=collections.OrderedDict()
def ParseRegister(fileName):
    with open(fileName, encoding='utf-8') as reg:
        for line in reg:
            if re.match(r'\#', line):
                continue
            else:
               mcm, bits, project, register, writeRegister, mp, tag1, tag2, sta1, sta2 = line.upper().strip().split(',')
               TAGSETTING[project]=mcm
               FEATUREBITS[project]=bits
               REGISTER[project][register]=[writeRegister, mp, tag1, tag2, sta1, sta2]
    return REGISTER, TAGSETTING, FEATUREBITS


class PMMFeatureEnablementCheck:
    # ********************* Constants
    # Name of the application under test.
    # MODIFY WITH NAME OF WORKLOAD BEING IMPLEMENTED.
    BRIEF_NAME = "PMMFeatureEnablementCheck"

    # Name of this wrapper application.
    # DO NOT MODIFY.
    PROGRAM_NAME = BRIEF_NAME

    # Copyright notice for AMD.
    # MODIFY YEAR IF REQUIRED.
    COPYRIGHT_NOTICE = "Copyright (C) 2021 Advanced Micro Devices [AMD]\n" \
                       + "This is free software.\n" + "This is no warranty.\n" \
                       + "\n" + \
        "AMD Microprocessor Solutions Sector [MSS] Performance Labs.\n"

    # Name of this wrapper script
    # DO NOT MODIFY
    WRAPPER_FILENAME = __file__

    # Version of this script
    # Update this if making major changes
    WRAPPER_VERSION = "1.0"

    # Create Object, create Instance variables, initialize results dir, log file, result file, state file
    def __init__(self, argv):

        # ********************* Instance Variables
        # object to root_node and test_node of result xml
        self.result_root = None
        self.test_node = None

        # Command line option variables
        self.verbose = False
        self.runs = 1
        self.is_rebooted = False
        self.benchmark_section = '' 
        self.install_path = ""
        self.log_path = self.install_path
        self.program_filename = ""

        # Other variables required for execution
        self.command_line = ""  # build command line to this script
        self.result_file = ""
        self.result_directory = Defaults.RESULT_DIRECTORY

        # # Initialize Instance Variables
        # self.result_directory =
        # # self.init_args()

        # # Initialize CommonWorkload Helper Object
        # self.cw_helper = CommonWorkloadHelper.CommonWorkloadHelper()

        self.check_output = True

        # Parse command line
        self.parse_command_line(argv)
        self.display_commandline_args()

        # Initialize CommonWorkload Helper Object
        self.cw_helper = CommonWorkloadHelper.CommonWorkloadHelper(
            log_level=Defaults.LOGLEVEL.DEBUG if self.verbose else Defaults.LOGLEVEL.INFO)

        # Archive existing result dir if exists
        self.cw_helper.archive_result_directory(self.result_directory)

        # Initialize logger
        self.cw_helper.initialize_logger(os.path.join(self.result_directory, Defaults.DEFAULT_LOGFILE_NAME),
                                         self.verbose)
        self.cw_helper.enable_logging()
        self.logger = self.cw_helper.logger

        self.result_file = os.path.join(self.result_directory, "test.xml")

        self.logger.info("Initialize result xml with header")
        self.result_root, self.test_node = self.cw_helper.create_xml_header(
            self.result_file, self.get_title(), self.get_command_line(), self.get_app_version(), self.get_scr_version())
        self.logger.info("Initialize state file with state RUNNING")
        self.cw_helper.set_status(self.result_directory, Defaults.STATUS.RUNNING)
        self.test_result = Defaults.STATUS.RUNNING

        # self.return_codes saves return codes for all iteration
        if self.is_rebooted:
            with open("self.return_codes", "rb") as f:
                self.return_codes = pickle.load(f)
            os.unlink("self.return_codes")
        else:
            self.return_codes = []

    # Get name of application under test
    def get_title(self):
        return self.BRIEF_NAME

    # Get version of this wrapper script
    def get_scr_version(self):
        return self.WRAPPER_VERSION

    # Get version of the app under test
    def get_app_version(self):
        return f"{self.BRIEF_NAME} {self.WRAPPER_VERSION}"

    # Get command line sent to this script
    def get_command_line(self):
        # Note: in Python, do not need to add filename to front of command_line string, Python does this automatically
        return self.command_line

    # Display version of this script
    def display_version(self):
        print(f"{self.PROGRAM_NAME} {self.WRAPPER_VERSION}")

    # Display command line args
    def display_commandline_args(self):
        print("args:")
        print(f"\tVerbose {self.verbose}")
        print(f"\tRuns {self.runs}")
        print(f"\tResults Directory: {self.result_directory}")

    # Parse command line args
    # MODIFY TO INCLUDE args REQUIRED FOR APP UNDER TEST
    def parse_command_line(self, args):
        self.command_line = " ".join(args)
        parser = argparse.ArgumentParser(description="Process some paramters")

        # Define the args, defaults, help messages and flags to set
        # parser.add_argument("--version", action="store_true", dest="version", default=False,
        #                     help="Display Version")
        parser.add_argument("--verbose", dest="verbose",default="False", help="Enable verbose logging")

        # external parameters settings
        parser.add_argument("--results-directory", dest="result_directory", default=Defaults.RESULT_DIRECTORY,help="Directory to store logs and results")
        parser.add_argument("--runs", dest="runs", type=int,default=1, help="Number of times to run application")
        parser.add_argument("--on-measure-start", dest="on_measure_start_command",help="Blocking command to execute Before measurement period")
        parser.add_argument("--on-measure-stop", dest="on_measure_stop_command",help="Blocking command to execute After measurement period")
        parser.add_argument("--check-output", dest="check_output",default="True", help="Check output for errors")
        parser.add_argument("--section", dest="section",default="ALL", help="which section type you want to use")
        # Parse the command-line.
        args = parser.parse_args()

        # Post-process a bit and assign to instance variables
        if args.verbose:
            self.verbose = False if args.verbose == "False" else True
        if args.result_directory:
            self.result_directory = re.sub(
                re.escape("%CD%"), re.escape(os.path.dirname(
                    os.path.abspath(__file__))), self.result_directory,
                flags=re.I)
            # self.result_directory = self.result_directory.replace("%CD%", os.path.dirname(os.path.abspath(__file__)))

        self.runs = args.runs
        self.benchmark_section = args.section
        self.dev=None
        self.papi=None
        self.die=None
        self.ccd=None
        
        


        self.check_output = args.check_output == "True"
        
    # Run on measure start
    def papi2_initialize(self):
        self.papi=PAPI2.using_toollib()
        self.dev=self.papi.get_cpu()
        
        if TAGSETTING[self.dev.asic_name] == 'YES':
            for dev in self.papi.all_devices:
                if isinstance(dev.die_id,int):
                    continue
                elif dev.die_id.strip().upper() == 'IOD':
                    continue
                elif re.match(r'ccd[0-9]',dev.die_id,re.M|re.I):
                    self.die=dev.die_id
                    break
                else:
                    return Defaults.EXITCODES.INVALID_CONFIG
                
            self.dev = self.papi.get_cpu_die(0,'IOD')
            self.ccd = self.papi.get_cpu_die(0,self.die)

    def get_SMUVersion(self):
        ver=self.dev.mp1fw.send_message('TEST','TESTSMC_MSG_GETSMUVERSION')
        vMMajor = (ver >> 24) & 0xFF
        vMajor = (ver >> 16) & 0xFF
        vMinor = (ver >> 8) & 0xFF
        vDebug = ver & 0xFF
        
        return str(vMMajor)+'.'+str(vMajor)+'.'+str(vMinor)+'.'+str(vDebug)
        

    
    def run_on_measure_start(self):
        self.cw_helper.print_and_execute_command("")

    def set_reboot_flag(self):
        self.logger.debug("Set reboot flag")
        open("reboot", "w").close()

    # MODIFY THIS FOR APPLICATION UNDER TEST
    def single_iteration_run(self, i):
        result_dir = list(pathlib.WindowsPath(self.install_path).glob("results*"))
        
        if len(result_dir) != 0:
            #shutil.rmtree(result_dir[0])
            self.logger.info("Result folder is : {0}".format(result_dir[0]))
        
        start_time = self.cw_helper.get_time_in_iso()
        
        cmdline = self.program_filename
        #if self.benchmark_section == "ALL":
        #    cmdline = cmdline + " --official"
        #elif self.benchmark_section == "media":
        #    cmdline = cmdline + " -b media.txt"
        #else:
        #    cmdline = cmdline + " -b " + self.benchmark_section + ".txt"
        self.logger.info("cmdline is : {0}".format(cmdline))
        self.cw_helper.print_and_execute_command(self.install_path + cmdline, log_output=True, cwd=self.install_path)

        stop_time = self.cw_helper.get_time_in_iso()
        # check results file and write result to result.log.
        result_dir = list(pathlib.WindowsPath(self.install_path).glob("results*"))
        rw_log_data_folder = result_dir[0]
        shutil.copytree(rw_log_data_folder, self.result_directory + "\\" + str(i) + "_loop\\")
        #result_log = list(pathlib.WindowsPath(result_dir[0]).glob("results.html"))[0]
        #self.logger.info("results.html log file name is: {0}".format(result_log))

        

        iteration_node = self.cw_helper.create_iteration_node(self.result_root, self.test_node, start_time, stop_time)
        value_tree_node = self.cw_helper.create_valuetree_node(self.result_root, iteration_node, tag="Test Name", value="{0}".format(self.benchmark_section), start="", stop="")

        pass_flag = True

        if int(FEATUREBITS[self.dev.asic_name])==32:
            feature_mask = self.dev.mp1fw.read_fw_state('FeatureHub_EnabledFeatures')
        else:
            feature_low = self.dev.mp1fw.read_fw_state('FeatureHub_EnabledFeatures_Low')
            feature_high = self.dev.mp1fw.read_fw_state('FeatureHub_EnabledFeatures_High')
            feature_mask = feature_low | (feature_high<<32)

        if not os.path.exists(os.getcwd()+r'\results'):
            os.makedirs(os.getcwd()+r'\results')
        elif os.path.isfile(os.getcwd()+'/results/'+self.dev.asic_name+'_FeatureCheck.csv'):
            os.remove(os.getcwd()+'/results/'+self.dev.asic_name+'_FeatureCheck.csv')
            
        fo = open('results/'+self.dev.asic_name+'_FeatureCheck.csv', "w+", encoding='utf-8', newline="")
        writer=csv.writer(fo)
        writer.writerow(["For feature enablement history, please refer to Power BI report here-","https://app.powerbi.com/groups/d8d1d0ff-c089-454c-a73b-4de14996241f/reports/012afce2-b150-4930-9608-60a4fe00d02c/ReportSection"])
        fo.write ('SMU Version,'+ self.get_SMUVersion()+'\n')
        asicName=self.dev.asic_name

        #Check Feature status
        for x in self.dev.mp1fw.feature_masks:
            if feature_mask & int(x):
                FEATURESTATUS[x.name]='Enabled'
                fo.write (x.name+",Enabled\n")
                self.logger.info("{0}\tEnabled".format(x.name))
            elif (~feature_mask & int(x)):
                FEATURESTATUS[x.name]='Disabled'
                fo.write (x.name+",Disabled\n")
                self.logger.info("{0}\tDisabled".format(x.name))
            else:
                return Defaults.EXITCODES.EXCEPTION
                    
        for reg in REGISTER[asicName].keys():
            #msg is the command to read register
            try:
                if REGISTER[asicName][reg][2] == 'VID':
                    msg="self.dev."+REGISTER[asicName][reg][1].lower()+".read_fw_state('"+reg+"') - 1"
                    VddOffVoltage = 0.25 + 0.005 * eval(msg)
                    FEATURESTATUS[REGISTER[asicName][reg][0]]=str(VddOffVoltage)
                    fo.write(REGISTER[asicName][reg][0]+','+ str(VddOffVoltage) +'V\n')
                    self.logger.info(REGISTER[asicName][reg][0]+','+ str(VddOffVoltage) +'V')
                elif REGISTER[asicName][reg][2] == 'NA':
                    msg="self.dev."+REGISTER[asicName][reg][1].lower()+".read_fw_state('"+reg+"')"
                    result = eval(msg)
                    FEATURESTATUS[REGISTER[asicName][reg][0]]=str(result)
                    fo.write(REGISTER[asicName][reg][0]+','+ str(result) +'\n')
                    self.logger.info(REGISTER[asicName][reg][0]+','+ str(result))
                else:
                    #msg: command to read register and compare with the value means enabled
                    if REGISTER[asicName][reg][1].lower() == 'mp5fw':
                        msg="self.ccd."+REGISTER[asicName][reg][1].lower()+".read_fw_state('"+reg+"') == " + REGISTER[asicName][reg][2]
                    else:
                        msg="self.dev."+REGISTER[asicName][reg][1].lower()+".read_fw_state('"+reg+"') == " + REGISTER[asicName][reg][2]

                    #if return true, will write Enabled and Disabled if false
                    if eval(msg):
                        FEATURESTATUS[REGISTER[asicName][reg][0]]=REGISTER[asicName][reg][4].capitalize()
                        fo.write(REGISTER[asicName][reg][0]+','+ REGISTER[asicName][reg][4].capitalize() +'\n')
                        self.logger.info(REGISTER[asicName][reg][0]+','+ REGISTER[asicName][reg][4].capitalize())
                    else:
                        FEATURESTATUS[REGISTER[asicName][reg][0]]=REGISTER[asicName][reg][5].capitalize()
                        fo.write(REGISTER[asicName][reg][0]+','+ REGISTER[asicName][reg][5].capitalize() +'\n')
                        self.logger.info(REGISTER[asicName][reg][0]+','+ REGISTER[asicName][reg][5].capitalize())
            except:
                FEATURESTATUS[REGISTER[asicName][reg][0]]='Disabled'
                fo.write(REGISTER[asicName][reg][0]+','+ 'Disabled\n')
                self.logger.info(REGISTER[asicName][reg][0]+',Disabled')
        fo.close()
        
        for k, v in FEATURESTATUS.items():
            self.cw_helper.create_value_node(self.result_root, value_tree_node, k,'',v, invert=0, primary=0, start="", stop="")
            self.logger.info("{0}: {1}".format(k, v))

        self.cw_helper.write_results(self.result_root, self.result_file)

        if pass_flag is False:
            self.cw_helper.set_status(self.result_directory, Defaults.STATUS.FAIL)
            self.logger.info("Error is found in log.")
            return Defaults.EXITCODES.APP_LOG_ERROR
        elif pass_flag:
            self.cw_helper.set_status(self.result_directory, Defaults.STATUS.PASS)
            self.logger.info("All Test passed.")
            return Defaults.EXITCODES.PASS

    # Run on measure stop
    def run_on_measure_stop(self):
        self.cw_helper.print_and_execute_command("")

    # Test for any pre conditions required to run this application or benchmark. Exit wrapper if conditions are not met
    # UPDATE THIS FOR APP UNDER TEST
    def test_pre_conditions(self):
        if self.dev.asic_name in TAGSETTING.keys():
            return True
        else:
            return Defaults.EXITCODES.INVALID_CONFIG

    # Main function to execute workload for the specified number of times
    def workload_execution(self):
        self.papi2_initialize()
        if self.test_pre_conditions():
            run = 0
            exit_code_list = []
            while run < self.runs:
                # for run in range(self.runs):
                self.logger.info(f"Starting iteration {run}")
                exit_code = self.single_iteration_run(run)
                exit_code_list.append(exit_code)
                run += 1
            self.logger.info(f"Exit code list is {exit_code_list}")
        else:
            self.test_result = Defaults.STATUS.FAIL
            exit_code = Defaults.EXITCODES.MISSING_RESOURCE

        if exit_code_list.count(0) != len(exit_code_list):
            print(exit_code_list)
            self.cw_helper.set_status(
                self.result_directory, Defaults.STATUS.FAIL)
            self.logger.info("Set status file to Fail.")
            return Defaults.EXITCODES.APP_RESULT_ERROR
        else:
            self.cw_helper.set_status(
                self.result_directory, Defaults.STATUS.PASS)
            self.logger.info("Set status file to Pass.")
            return Defaults.EXITCODES.PASS


if __name__ == "__main__":
    # Main section
    print("\nExecuting {0} ... \n".format(__file__))
    ParseRegister('PMMFeatureEnablementCheck.csv')
    wrapper = PMMFeatureEnablementCheck(sys.argv)
    wrapper.workload_execution()
