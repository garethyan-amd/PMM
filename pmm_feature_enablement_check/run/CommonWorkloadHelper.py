#!/usr/bin/env python
# version 2.0.0

import time
from typing import Tuple, List, Type, Callable, Any
import Defaults
import os
import subprocess
from datetime import datetime
import xml.dom.minidom
import platform
import sys, logging
from pathlib import WindowsPath

class LogFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""
    # http://stackoverflow.com/a/24956305/408556
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        # "<" instead of "<=": since logger.setLevel is inclusive, this should
        # be exclusive
        return record.levelno < self.level

class CommonWorkloadHelper(object):
    def __init__(self, log_level=Defaults.LOGLEVEL.INFO):
        # Instance Variables
        self.log_file = "test.log"
        self.verbose_logging = False
        self.log_initialized = False
        self.logger = None 
        self.log_level = log_level

    # Archive results
    def archive_result_directory(self, result_directory):
        if os.path.exists(result_directory):
            # Get time to create archive directory
            current_time = datetime.now().strftime("%Y%m%dT%H%M%S%f")[0:-5]
            # Create archive directory name
            archive_result_dir = result_directory + "_" + current_time
            # rename result_directory to archive name
            os.rename(result_directory, archive_result_dir)
            self.log_file = os.path.join(archive_result_dir, "test.log")
        # create new result_directory
        os.mkdir(result_directory)
        # self.enable_logging()

    # Logging functions
    def initialize_logger(self, log_filename, verbose):
        self.log_file = log_filename
        self.verbose_logging = verbose
        self.log_initialized = True

    def enable_logging(self):
        logging.addLevelName(logging.NOTSET, "VERBOSE")
        log_format = logging.Formatter(
            "%(asctime)s,%(levelname)s,%(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z")
        file_handler = logging.FileHandler(self.log_file, mode="a+")
        file_handler.setFormatter(fmt=log_format)
        #stream_handle = logging.StreamHandler(sys.stdout)
        #stream_handle.setFormatter(fmt=log_format)
        # https://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams/1383365
        # Python by default logs to stderr. Using the fix from the above example to fix it
        MIN_LEVEL = logging.DEBUG
        stdout_hdlr = logging.StreamHandler(sys.stdout)
        stderr_hdlr = logging.StreamHandler(sys.stderr)
        log_filter = LogFilter(logging.WARNING)
        stdout_hdlr.addFilter(log_filter)
        stdout_hdlr.setFormatter(fmt=log_format)
        stderr_hdlr.setLevel(max(MIN_LEVEL, logging.WARNING))
        
        logger = logging.getLogger()
        logger.addHandler(stdout_hdlr)
        logger.addHandler(stderr_hdlr)
        logger.addHandler(file_handler)
        logger.setLevel(self.log_level)
        self.logger = logger

    def log_message(self, msg, level):
        """
        DEPRECATED: Please use logging.info/debug instead.
        Log messages.
        :param msg: message to log.
        :param level: defined in Defaults.LOGLEVEL
        :return: None
        """
        if level == Defaults.LOGLEVEL.VERBOSE and self.verbose_logging is False:
            return
        self.logger.log(level, msg)

    # Result XML
    def create_xml_header(self, result_filename, title, command_line, app_version, script_version, dataset_version=""):

        # Create xml object
        xml_doc = xml.dom.minidom.Document()

        # test_node
        test_node = xml_doc.createElement("test")
        test_node.setAttribute(
            "xsi:noNamespaceSchemaLocation", "commonworkload-results-format-10-1-2011.xsd")
        test_node.setAttribute(
            "xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
        test_node.setAttribute(
            "xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        xml_doc.appendChild(test_node)

        # titleElement
        title_element = xml_doc.createElement("title")
        test_node.appendChild(title_element)

        # titleElement text
        title_element_text = xml_doc.createCDATASection(title)
        title_element.appendChild(title_element_text)

        # cmdlineElement
        cmdline_element = xml_doc.createElement("commandLine")
        test_node.appendChild(cmdline_element)

        # cmdlineElement text
        cmdline_element_text = xml_doc.createCDATASection(command_line)
        cmdline_element.appendChild(cmdline_element_text)

        # appverElement
        appver_element = xml_doc.createElement("applicationVersion")
        test_node.appendChild(appver_element)

        # appverElement text
        appver_element_text = xml_doc.createCDATASection(app_version)
        appver_element.appendChild(appver_element_text)

        # scrverElement
        scrver_element = xml_doc.createElement("scriptVersion")
        test_node.appendChild(scrver_element)

        # scrverElement text
        scrver_element_text = xml_doc.createCDATASection(script_version)
        scrver_element.appendChild(scrver_element_text)

        if dataset_version != "":
            # datasetElement
            dataset_element = xml_doc.createElement("datasetVersion")
            test_node.appendChild(dataset_element)
            # datasetElement text
            dataset_element_text = xml_doc.createCDATASection(dataset_version)
            dataset_element.appendChild(dataset_element_text)

        return xml_doc, test_node

    def create_iteration_node(self, root_node, test_node, start_time, stop_time):
        iteration_node = root_node.createElement("iteration")
        iteration_node.setAttribute("start", start_time)
        iteration_node.setAttribute("stop", stop_time)
        test_node.appendChild(iteration_node)
        return iteration_node

    def create_value_node(self, root_node, parent_node, desc, units, result, invert=0, primary=1, start="", stop=""):
        value_node = root_node.createElement("value")
        value_node.setAttribute("invert", str(invert))
        value_node.setAttribute("primary", str(primary))
        if start != "":
            value_node.setAttribute("start", str(start))
        if stop != "":
            value_node.setAttribute("stop", str(stop))
        parent_node.appendChild(value_node)

        desc_node = root_node.createElement("description")
        value_node.appendChild(desc_node)
        desc_node_text = root_node.createCDATASection(desc)
        desc_node.appendChild(desc_node_text)

        units_node = root_node.createElement("units")
        value_node.appendChild(units_node)
        units_node_text = root_node.createCDATASection(units)
        units_node.appendChild(units_node_text)

        result_node = root_node.createElement("result")
        value_node.appendChild(result_node)
        result_node_text = root_node.createCDATASection(result)
        result_node.appendChild(result_node_text)
        return value_node

    def create_valuetree_node(self, root_node, parent_node, tag, value, start="", stop=""):
        valuetree_node = root_node.createElement("ValueTree")
        valuetree_node.setAttribute("tag", tag)
        valuetree_node.setAttribute("value", str(value))
        parent_node.appendChild(valuetree_node)
        return valuetree_node

    def write_results(self, root_node, result_filename):
        # Debug: print root_node.toprettyxml(indent="  ")
        result_file = open(result_filename, 'w')
        result_file.write(root_node.toprettyxml(indent="  "))
        result_file.close()

    # Status file
    def set_status(self, result_folder, status):
        new_status_file = f"{Defaults.STATUS_FILE_PREFIX}_{status}.log"
        full_status_path = os.path.join(result_folder, new_status_file)

        # Delete any existing status files in results dir
        for filename in os.listdir(result_folder):
            if Defaults.STATUS_FILE_PREFIX in filename and ".log" in filename:
                os.remove(result_folder + os.path.sep + filename)

        # Create new status file (Note: could not get 'touch' command os.mknod to work in Python)
        self.write_file(full_status_path, "")

    # Common utility functions
    def add_program_to_firewall_whitelist(self, program: str = "") -> None:
        """
        program: all *.exe of the folder will be allowed to access network.
        return: None
        """
        if self.is_Linux():
            pass
        else:
            p = WindowsPath(program)
            if p.is_dir():
                for i in list(p.rglob("*.exe")):
                    try:
                        os.system(f'netsh advfirewall firewall add rule name="{i}" dir=in action=allow program="{i}" \
                            enable=yes')
                    except Exception as e:
                        print(e)
            else:
                if WindowsPath.exists(program):
                    os.system(f'netsh advfirewall firewall add rule name="{program}" dir=in action=allow program="{program}" \
                        enable=yes')
                else:
                    print("File not found!")

    def is_Windows(self):
        if ("nt" in os.name):
            return True
        else:
            return False

    def is_Linux(self):
        if ("posix" in os.name):
            return True
        else:
            return False

    def is_DiagOS(self):
        if self.is_Linux():
            result = subprocess.check_output(['uname', '-r'], shell=True)
        if "DiagOS" in result:
            return True
        else:
            return False
        return False

    def get_processor_architecture(self):
        return platform.processor()

    def is_x64(self):
        if ("64" in platform.processor()):
            return True
        else:
            return False

    def get_time_in_iso(self):
        return datetime.now().isoformat()[:-3]

    def get_time_in_format(self, format):
        t = datetime.now()
        return t.strftime(format)

    def write_file(self, file, data):
        with open(file, 'a+') as f:
            f.write(data)

    def print_and_execute_command(self,
                                  command: str,
                                  timeout: int = None,
                                  cwd: str = None,
                                  log_output: bool = True,
                                  outputs_check_callback: Callable = None,
                                  callback_return_values_for_termination: List = None,
                                  **kwargs: Any,
                                  ) -> None or Tuple[int, List[str], Type]:
        """
        Execute command. If logger is defined, output will be sent to the logger.

        :param command: Command string to be executed.
        :param timeout: Timeout seconds. An exception subprocess.TimeoutExpired will be raised when timeout reached.
        :param cwd: If True, use command path as cwd
        :param log_output: If True, output will be send to logger while running.
        :param outputs_check_callback: Function called to check output during process running. The function should take
            one argument which is a list of string. The last string is the latest output from the process.
        :param callback_return_values_for_termination: If callback function returned a value in this list, the command
            will be terminated immediately.
        :param kewargs: other parameters used in Popen
        :return: (return_code, output_list, callback_return_code) or None
        """
        if callback_return_values_for_termination is None:
            callback_return_values_for_termination = []
        if command == "":
            return None

        callback_return_value_list = []
        p = self.start_process(command, cwd=cwd, **kwargs)
        start_time = time.time()

        outputs = []
        if log_output and self.logger:
            self.logger.info(f"Output from command: {command}")

        while True:
            if timeout and time.time() - start_time > timeout:
                raise subprocess.TimeoutExpired(
                    f"Timed out after {timeout} seconds: {command}")
            std_out_buffer = p.stdout.readline()  # .decode("utf-8")
            outputs.append(std_out_buffer)
            if log_output and self.logger:
                self.logger.info(
                    std_out_buffer[:-1] if std_out_buffer.endswith("\n") else std_out_buffer)
            if outputs_check_callback:
                callback_return_value = outputs_check_callback(outputs[:])
                callback_return_value_list.append(callback_return_value)
                if self.logger:
                    self.logger.debug(
                        f"Callback return value: {callback_return_value_list}")
                if callback_return_value in callback_return_values_for_termination:
                    if self.logger:
                        self.logger.info("Process terminated.")
                    p.terminate()
                    break

            if std_out_buffer == "" and p.poll() is not None:
                break

        return p.returncode, outputs, callback_return_value_list

    def start_process(self, command: str, cwd: str = None, **kwargs: Any) -> subprocess.Popen:

        """
        Execute command.
        :param command: command string
        :param cwd: If True, use command path as cwd
        :return: a Popen object
         """
        cmd_path, cmd = os.path.split(command)
        if self.is_Linux():
            exec_prefix = "exec"
        else:
            exec_prefix = ""
        p = subprocess.Popen(
            f"{exec_prefix} {os.path.join(os.path.expanduser(cmd_path), cmd)}", universal_newlines=True, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=os.path.expanduser(os.path.dirname(command.split(" ")[0])) if cwd else None)
        return p

    def execute_with_no_stdout(self, command):
        command_list = command.split(' ')
        FNULL = open(os.devnull, 'w')
        subprocess.call(command_list, stdout=FNULL, stderr=subprocess.STDOUT)

    # def command_with_timeout(self, time_out, command, logger=None):
    #     try:
    #         self.print_and_execute_command(command, logger=logger, time_out=time_out)
    #         return True
    #     except Exception as e:
    #         if logger:
    #             logger.error(f"EXCEPTION: {str(e)}")
    #         return False

    @property
    def cpu_count(self):
        return os.cpu_count()
