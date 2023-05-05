import os
import base64
import time
import csv
import subprocess
import tempfile
import shutil

# Named for the saying of a wolf in sheeps clothing, this is for creating disguised process names
class processwolf:

    ### CLASS-LOCAL VARIABLES ###
    def __init__(self):

        # Since this would be used in a VM, keeping this as an internet backed database
        # wouldnt make sense since rollbacks to the database would both reverse the filename
        # change and also restore the database to a state before the file was added
        self.localdb = "C:\db.txt"
        self.dbLoaded = False
        self.base64conversions = {}
        
        self.drive_loaded = False
        self.drive_files = None

        #imported from https://github.com/addi00000/empyrean    warning: REAL MALWARE DONT RUN
        self.blacklistedProcesses = ["httpdebuggerui", "wireshark", "fiddler", "regedit", 
                                    "cmd", "taskmgr", "vboxservice", "df5serv", "processhacker", 
                                    "vboxtray", "vmtoolsd", "vmwaretray", "ida64", "ollydbg",
                                    "pestudio", "vmwareuser", "vgauthservice", "vmacthlp", "x96dbg", 
                                    "vmsrvc", "x32dbg", "vmusrvc", "prl_cc", "prl_tools", "xenservice", 
                                    "qemu-ga", "joeboxcontrol", "ksdumperclient", "ksdumper", "joeboxserver"]

    ### HELPER FUNCTIONS ###

    def list_files_on_drive(self, drive, printfiles=False):
        """
        Lists all files on a given Windows drive.
        
        Args:
        - drive (str): The drive letter to list files from (e.g. "C:", "D:", etc.).
        
        Returns:
        - A list of strings representing the absolute paths of all files on the drive.
        """
        if self.drive_loaded:
            return self.drive_files

        files = []
        if printfiles:
            time.sleep(1)
        for root, dirnames, filenames in os.walk(drive):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                files.append(filepath)
                if printfiles:
                    print(str(filename))
        self.drive_loaded = True
        return files

    def rename_file_to_base64(self, filename, addToDatabase=False):
        """
        Renames a file on Windows to a base64 hash of its original filename.
        
        Args:
        - filename (str): The filename to rename.
        - addToDatabase (bool): Boolean to determine if the conversion should be added to db.txt
        Returns:
        - The new filename as a string.
        """
        # Get the directory path and base filename (without extension)
        dirpath = os.path.dirname(filename)
        
        #basename = os.path.splitext(os.path.basename(filename))[0]
        basename = os.path.basename(filename)
        
        # Generate the new filename as a base64 hash of the original filename
        hashname = self.encodeFileName(basename)
        
        filename = os.path.join(dirpath, basename)
        new_filename = os.path.join(dirpath, hashname)

        # Rename the file
        #print(repr(filename))
        os.rename(filename, new_filename)

        # Create tuple with all parts needed for conversion
        t = (dirpath, basename, hashname)

        # Add both to dictionary
        self.base64conversions[t[2]] = t    # Stores hash into dictionary
        self.base64conversions[t[1]] = t    # Stores filename into dictionary

        # <dirpath>,<filename>,<hash>
        if addToDatabase:
            self.add_line_to_csv_file(f"{dirpath}.{basename},{hashname}")

        # Return the new filename
        return new_filename

    def restore_filename_from_base64(self, filename, addToDatabase=False):
        """
        Decodes a base64 hash and restores the original filename.
        
        Args:
        - filename (str): The filename to restore.
        - addToDatabase (bool): Boolean to determine if the conversion should be added to db.txt
        Returns:
        - The original filename as a string.
        """
        # Get the directory path and base64-encoded filename
        dirpath = os.path.dirname(filename)
        base64_filename = os.path.basename(filename)
        
        # Decode the base64 hash
        decoded_filename = self.decodeFileName(base64_filename)
        
        # Construct the original filename (with extension) and return it
        original_filename = os.path.join(dirpath, f"{decoded_filename}")
        os.rename(filename, original_filename)

        if addToDatabase:
            self.remove_line_from_csv(self, f"{dirpath}.{decoded_filename},{base64_filename}")

        return original_filename

    def create_or_open_file(self, filename):
        """
        Creates or opens a file with the specified filename.

        If the file already exists, it will be opened in read and write mode ('r+').
        If the file does not exist, it will be created and opened in write and read mode ('w+').
        
        Args:
            filename (str): The name of the file to create or open.
        Returns:
            file: The file object representing the created or opened file.
        Raises:
            FileNotFoundError: If the file cannot be found.
        """
        try:
            file = open(filename, 'r+')
        except FileNotFoundError:
            file = open(filename, 'w+')
        return file

    
    def read_csv_file(self):
        # CSV can have format <dirpath>,<filename>,<hash> and stored into the base64 dict as:
        # Key:      <hash> or <name>
        # Value:    (csv tuple)

        """
        Reads data from a CSV file.

        Opens the CSV file specified by `self.localdb` in read and write mode ('r+').
        Reads each row from the CSV file and adds them as tuples to the `data` list.
        If a row contains more than one element, the tuple is appended to `data` list.
        Additionally, it stores hash and filename values into the `base64conversions` dictionary.
        Sets the `dbLoaded` flag to True upon successful file reading.

        Returns:
            list: The data read from the CSV file as a list of tuples.
        """
        data = []
        try:
            file = open(self.localdb, 'r+')
            csv_reader = csv.reader(file)
            for row in csv_reader:
                t = tuple(row)
                if len(t) > 1:
                    data.append(t)
                    self.base64conversions[t[2]] = t    # Stores hash into dictionary
                    self.base64conversions[t[1]] = t    # Stores filename into dictionary
                    if t[1].split(".") > 1:
                        self.base64conversions[t[1].split(".")[0]] = t    # Stores filename into dictionary without extension
            self.dbLoaded = True
        except FileNotFoundError:
            pass
        return

    def add_line_to_csv_file(self, line):
        """
        Adds a line to a CSV file.

        Appends the specified line to the CSV file specified by `self.localdb`.

        Args:
            line (list or tuple): The line to add to the CSV file.

        """
        with open(self.localdb, 'a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(line)

    def remove_line_from_csv(self, line):
        """
        Removes a specific line from a CSV file.

        Removes the line matching the specified `line` from the CSV file specified by `self.localdb`.
        The function creates a temporary file to store the modified contents.
        The specified line is skipped during the reading and writing process, effectively removing it from the file.

        Args:
            line (list or tuple): The line to be removed from the CSV file.
        """
        # Create a temporary file to store the modified contents
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)

        with open(self.localdb, 'r') as file, temp_file:
            csv_reader = csv.reader(file)
            csv_writer = csv.writer(temp_file)

            for row_number, row in enumerate(csv_reader, start=1):
                # Skip the line to be removed
                if row == line:
                    continue

                csv_writer.writerow(row)
        # Replace the original file with the modified file
        shutil.move(temp_file.name, csv_file)

    def encodeFileName(self, filename):
        """
        Encodes a filename using base64 encoding.

        Splits the filename by periods ('.') and encodes the first part using base64 encoding.
        Returns the encoded filename concatenated with the remaining parts, separated by periods.

        Args:
            filename (str): The filename to encode.

        Returns:
            str: The encoded filename.
        """
        split = filename.split(".")
        return base64.urlsafe_b64encode(split[0].encode()).decode() + ("." + ".".join(split[1:]) if len(split) > 1 else "")

    def decodeFileName(self, filename):
        """
        Decodes a filename that was previously encoded using base64 encoding.

        Splits the filename by periods ('.') and decodes the first part using base64 decoding.
        Returns the decoded filename concatenated with the remaining parts, separated by periods.
        
        Args:
            filename (str): The encoded filename to decode.
        Returns:
            str: The decoded filename.
        """
        split = filename.split(".")
        return base64.urlsafe_b64decode(split[0].encode()).decode() + ("." + ".".join(split[1:]) if len(split) > 1 else "")

    def listMatches(self, drivename = "C:"):
        """
        Lists the matches of blacklisted processes from the specified drive.

        Args:
            drivename (str): The drive name to gather data from (default is "C:").
        Returns:
            list: A list of matches found, each containing the directory name, basename,
                and encoded file name.
        """
        matches = []
        print("Gathering Data from Drive " + drivename)

        # gather filenames from system, doesnt run if already done previously
        self.drive_files = self.list_files_on_drive(drive=drivename, printfiles=False)
        print("---\nDone")

        # compare files to list
        for filename in self.drive_files:
            basename = os.path.basename(filename)
            filename = basename.split(".")[0]
            dirname = os.path.dirname(filename)
            filelist = []
            if filename.lower() in self.blacklistedProcesses:
                if "exe" in basename:
                    t = (dirname, basename, self.encodeFileName(basename))
                    matches.append()
                    self.base64conversions[t[2]] = t    # Stores hash into dictionary
                    self.base64conversions[t[1]] = t    # Stores filename into dictionary
                    if t[1].split(".") > 1:
                        self.base64conversions[t[1].split(".")[0]] = t    # Stores filename into dictionary without extension
        return matches

    ### MAIN LOOP FUNCTIONS ###

    def repl_loop(self):
        """
        Starts a Read-Evaluate-Print Loop (REPL) for user interaction.

        - Initializes by reading data from a CSV file and listing matches.
        - Enters a loop to continuously accept user input until the user enters "exit".
        - Supports the following commands:
            - ls [option]: Lists unique matches based on the given option ("hash" or "path").
            - open <filename>: Opens the specified file using subprocess.Popen.
            - convert <filename1> [filename2] ...: Renames the files to their base64 representation.
            - reset <filename1> [filename2] ...: Restores the original filenames from their base64 representation.

        Exceptions are caught and appropriate error messages are printed.

        """
        # INIT
        self.read_csv_file()
        matches = self.listMatches()

        # REPL
        while True:
            user_input = input(">>> ")
            if user_input == "exit":
                break
            try:
                split = user_input.split()

                if "ls" in split[0]:
                    #if len(split) > 1:
                    number = 1
                    if len(split) > 1 and "hash" in split[1]:
                        number = 2
                    if len(split) > 1 and "path" in split[1]:
                        number = 0

                    index = 0
                    # Matches come as ( <dirpath>,<filename>,<hash> )
                    uniqueMatches = list(set(matches))
                    for match in uniqueMatches:
                        index += 1
                        print(str(index) + "): " + match[number])

                if "open" in split[0]:
                    try:
                        # <dirpath>,<filename>,<hash>
                        filestruct = self.base64conversions[split[1]]
                        process = subprocess.Popen(filestruct)
                        process.wait()
                        return process.returncode
                    except FileNotFoundError:
                        print("EXE file not found.")
                        return None

                if "convert" in split[0]:
                    if len(split) > 1:
                        for file in split[1:]:
                            #convert to base64
                            new_filename = self.rename_file_to_base64(file)
                            
                            #output results
                            print(f"Renamed {file} to {new_filename}")
                if "reset" in split[0]:
                    if len(split) > 1:
                        for file in split[1:]:
                            #restore file name from base64
                            original_filename = self.restore_filename_from_base64(file)
                            #print exchanged name result
                            print(f"Restored {file} to {original_filename}")
            except Exception as e:
                print(f"REPL Event Loop Error: {e}")


if __name__ == '__main__':
    pw = processwolf()
    pw.repl_loop()
