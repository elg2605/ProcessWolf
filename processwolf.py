import os
import base64
import time
import csv
import subprocess

# Named for the saying of a wolf in sheeps clothing, this is for creating disguised process names
class processwolf:

    ### CLASS-LOCAL VARIABLES ###
    def __init__(self):

        # Since this would be used in a VM, keeping this as an internet backed database
        # wouldnt make sense since rollbacks to the database would both reverse the filename
        # change and also restore the database to a state before the file was added
        self.localdb = "db.txt"
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

    def rename_file_to_base64(self, filename):
        """
        Renames a file on Windows to a base64 hash of its original filename.
        
        Args:
        - filename (str): The filename to rename.
        
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

        # Return the new filename
        return new_filename

    def restore_filename_from_base64(self, filename):
        """
        Decodes a base64 hash and restores the original filename.
        
        Args:
        - filename (str): The filename to restore.
        
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
        return original_filename

    def create_or_open_file(self, filename):
        try:
            file = open(filename, 'r+')
        except FileNotFoundError:
            file = open(filename, 'w+')
        return file

    # CSV can have format <dirpath>,<filename>,<hash> and stored into the base64 dict as:
    # Key:      <hash> or <name>
    # Value:    (csv tuple)
    def read_csv_file(self):
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
            self.dbLoaded = True
        except FileNotFoundError:
            pass
        return

    def add_line_to_csv_file(self, line):
        with open(self.localdb, 'a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(line)

    def encodeFileName(self, filename):
        split = filename.split(".")
        return base64.urlsafe_b64encode(split[0].encode()).decode() + ("." + ".".join(split[1:]) if len(split) > 1 else "")

    def decodeFileName(self, filename):
        split = filename.split(".")
        return base64.urlsafe_b64decode(split[0].encode()).decode() + ("." + ".".join(split[1:]) if len(split) > 1 else "")

    def listMatches(self, drivename = "C:"):
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
                    matches.append((dirname, basename, self.encodeFileName(basename)))
        return matches

    ### MAIN LOOP FUNCTIONS ###

    def repl_loop(self):
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
                #print(split[0])

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
                    print("open")

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
                print(f"Error: {e}")


if __name__ == '__main__':
    pw = processwolf()
    pw.repl_loop()
