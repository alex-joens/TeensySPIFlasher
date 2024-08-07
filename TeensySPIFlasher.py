# *************************************************************************
# TeensySPIFlasher.py v0.1
#
# Teensy 4.1 version by jakatackka@gmail.com
# 
# *************************************************************************
# SPIway.py - Teensy++ 2.0 SPI flasher for PS4
#
# Copyright (C) 2017 judges@eEcho.com
#
# This code is licensed to you under the terms of the GNU GPL, version 2;
# see file COPYING or http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
# *************************************************************************

import serial, time, datetime, sys

class TeensySerialError(Exception):
    pass

class TeensySerial(object):
    BUFSIZE = 32768

    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout = 300, rtscts = False, dsrdtr = False, xonxoff = False, writeTimeout = 60)
        if self.ser is None:
            raise TeensySerialError("could not open serial %s") % port
        self.ser.flushInput()
        self.ser.flushOutput()
        self.obuf = ""

    def write(self, s):
        if isinstance(s,int):
            s = chr(s)
        elif isinstance(s,tuple) or isinstance(s,list):
            s = ''.join([chr(c) for c in s])
        self.obuf += s
        while len(self.obuf) > self.BUFSIZE:
            self.ser.write(self.obuf[:self.BUFSIZE])
            self.obuf = self.obuf[self.BUFSIZE:]

    def flush(self):
        if len(self.obuf):
            self.ser.write(self.obuf)
            self.ser.flush()
            self.obuf = ""

    def read(self, size):
        self.flush()
        data = self.ser.read(size)
        return data

    def readbyte(self):
        return ord(self.read(1))

    def close(self):
        print
        print "Closing serial device..."
        if self.ser is None:
            print "Device already closed."
        else:
            self.ser.close()
            print "Done."

class SPIError(Exception):
    pass

class SPIFlasher(TeensySerial):
    VERSION_MAJOR = 0
    VERSION_MINOR = 0
    # SPI_DISABLE_PULLUPS = 0
    MF_ID = 0
    DEVICE_ID = 0
    SPI_SECTOR_SIZE = 0
    SPI_BLOCK_COUNT = 0
    SPI_SECTORS_PER_BLOCK = 0
    SPI_BLOCK_SIZE = 0
    SPI_ADDRESS_LENGTH = 0
    SPI_USE_3BYTE_CMDS = False

    # Teensy commands
    CMD_SCRIPT_INFO = 0
    CMD_SPI_INFO = 1
    CMD_SPI_READ_BLOCK = 2
    CMD_SPI_ERASE_CHIP = 3
    CMD_SPI_ERASE_BLOCK = 4
    CMD_SPI_WRITE_BLOCK = 5
    
    # Response codes
    REQ_SUCCESS = 0
    REQ_FAILURE = 1
    REQ_CMD_NOT_RECOGNIZED = 2
    REQ_ADDR_READ_TIMEOUT = 3
    REQ_WRITE_PROTECTED = 4
    REQ_CHIP_ERASE_FAILURE = 5
    REQ_PAGE_READ_TIMEOUT = 6
    REQ_PAGE_WRITE_FAILURE = 7
    
    def __init__(self, port, ver_major, ver_minor):
        if port:
            TeensySerial.__init__(self, port)
        # self.SPI_DISABLE_PULLUPS = 0
        self.VERSION_MAJOR = ver_major
        self.VERSION_MINOR = ver_minor


    ###################
    # Teensy commands #
    ###################

    # Check if we are connected to the Teensy and verify that it is running the correct version of our software
    def ping(self):
        self.write(self.CMD_SCRIPT_INFO)
        response_code = self.readbyte()
        ver_major = self.readbyte()
        ver_minor = self.readbyte()
        if (response_code != self.REQ_SUCCESS):
            print "Ping failed with exit code %d" % response_code
        elif (ver_major != self.VERSION_MAJOR) or (ver_minor != self.VERSION_MINOR):
            print "Ping failed (expected v%d.%02d, got v%d.%02d)"%(self.VERSION_MAJOR, self.VERSION_MINOR, ver_major, ver_minor)
            self.close()
            sys.exit(1)


    # Read the manufacturer and device IDs
    def readSpiIds(self):
    #     if (self.SPI_DISABLE_PULLUPS == 0):
    #         self.write(self.CMD_PULLUPS_ENABLE)
    #     else:
    #         self.write(self.CMD_PULLUPS_DISABLE)

        self.write(self.CMD_SPI_INFO)
        self.checkResponseCode()

        spi_info = self.read(2)   

        # print "Raw ID data: 0x%02x 0x%02x" % (ord(spi_info[0]), ord(spi_info[1]))

        self.MF_ID = ord(spi_info[0])
        self.DEVICE_ID = ord(spi_info[1])


    def write4ByteAddress(self, address):
        self.write((address >> 24) & 0xFF)
        self.write((address >> 16) & 0xFF)
        self.write((address >> 8) & 0xFF)
        self.write(address & 0xFF)


    # Checks the response code and throws an exception if the last request failed.
    # If you see one or two failures, just replug the Teensy and try running the command again.
    # If failures are happening frequently, try adjusting the clock speed that the NOR chip is running at.
    def checkResponseCode(self):
        responseCode = self.readbyte()
        
        if (responseCode == self.REQ_SUCCESS):
            return
        
        errorMessage = ""
        
        if (responseCode == self.REQ_FAILURE):
            errorMessage = "Unexpected failure"
        elif (responseCode == self.REQ_CHIP_ERASE_FAILURE):
            errorMessage = "Chip erase failed"
        elif (responseCode == self.REQ_PAGE_WRITE_FAILURE):
            errorMessage = "Page failed to write"
        elif (responseCode == self.REQ_CMD_NOT_RECOGNIZED):
            command = self.readbyte()
            errorMessage = "Command not recognized: %d" % command
        elif (responseCode == self.REQ_ADDR_READ_TIMEOUT):
            errorMessage = "Teensy timed out when receiving the address bytes. Did you send the correct number of bytes?"
        elif (responseCode == self.REQ_PAGE_READ_TIMEOUT):
            errorMessage = "Teensy timed out when receiving the block data from your PC."
        elif (responseCode == self.REQ_WRITE_PROTECTED):
            errorMessage = "Operation failed because NOR chip has write protection enabled."
        else:
            errorMessage = "Received unknown error code: %d" % responseCode

        # Most failures will leave the Teensy in an unpredictable state, so it is best to unplug and replug it.
        self.close()
        raise SPIError(errorMessage)


    def readBlock(self, block):
        # if self.SPI_ADDRESS_LENGTH == 3:
        #     self.write(self.CMD_SPI_3BYTE_ADDRESS)
        # else:
        #     self.write(self.CMD_SPI_4BYTE_ADDRESS)

        # if self.SPI_USE_3BYTE_CMDS == 0:
        #     self.write(self.CMD_SPI_4BYTE_CMDS)
        # else:
        #     self.write(self.CMD_SPI_3BYTE_CMDS)

        self.write(self.CMD_SPI_READ_BLOCK)
        self.write4ByteAddress(block * self.SPI_BLOCK_SIZE)
        self.checkResponseCode()

        data = self.read(self.SPI_BLOCK_SIZE)
        return data


    def eraseBlock(self, block):
        # if self.SPI_ADDRESS_LENGTH == 3:
        #     self.write(self.CMD_SPI_3BYTE_ADDRESS)
        # else:
        #     self.write(self.CMD_SPI_4BYTE_ADDRESS)

        # if self.SPI_USE_3BYTE_CMDS == 0:
        #     self.write(self.CMD_SPI_4BYTE_CMDS)
        # else:
        #     self.write(self.CMD_SPI_3BYTE_CMDS)

        self.write(self.CMD_SPI_ERASE_BLOCK)
        self.write4ByteAddress(block * self.SPI_BLOCK_SIZE)
        self.checkResponseCode()


    def eraseChip(self):
        self.write(self.CMD_SPI_ERASE_CHIP)
        self.checkResponseCode()


    # Programs a block by erasing it, writing the new block, then reading it back to verify the contents
    # Returns True if programming was successful
    def programBlock(self, data, block):
        datasize = len(data)
        if datasize != self.SPI_BLOCK_SIZE:
            print "Incorrect length %d != %d!" % (datasize, self.SPI_BLOCK_SIZE)
            return -1
        
        # Erase the block before writing to it
        self.eraseBlock(block)

        # Write the block's new contents
        self.write(self.CMD_SPI_WRITE_BLOCK)
        self.write4ByteAddress(block * self.SPI_BLOCK_SIZE)
        self.write(data)
        self.checkResponseCode()

        # Verification
        readData = self.readBlock(block)
        if data != readData:
            print "Error! Block verification failed (block=%d)." % (block)
            # sideBySide = list(zip(list(data), list(readData)))
            # numberOfErrors = len(filter(lambda pair: pair[0] != pair[1], sideBySide))
            # mismatchIndicesForward = (i for i, v in enumerate(sideBySide) if v[0] != v[1])
            # mismatchIndicesBackward = (i for i, v in enumerate(reversed(sideBySide)) if v[0] != v[1])

            # print "Total number of mismatched bytes: %d (%d%%)." % (numberOfErrors, 100 * numberOfErrors / self.SPI_BLOCK_SIZE)
            # print "First mismatch is at offset %x, second is at %x, last is at %x."%(next(mismatchIndicesForward), next(mismatchIndicesForward), self.SPI_BLOCK_SIZE - next(mismatchIndicesBackward) - 1)
            return False
                
        return True
    

    ###################
    # Script commands #
    ###################
       
    # Fetches the manufacturer and device ID, then sets our SPI configuration
    # NOTE: only one chip is currently supported. Code changes are required to support the other chips.
    def getSpiInfo(self):
        print
        print "SPI Information"
        print "---------------"
        self.readSpiIds()

        if self.MF_ID == 0xC2:
            print "Chip manufacturer: Macronix (0x%02x)" % self.MF_ID
            if self.DEVICE_ID == 0x18:
                print "Chip type:         MX25L25635F (0x%02x)" % self.DEVICE_ID
                self.SPI_BLOCK_COUNT = 512
                self.SPI_SECTORS_PER_BLOCK = 16
                self.SPI_SECTOR_SIZE = 0x1000
                self.SPI_TOTAL_SECTORS = self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT
                self.SPI_BLOCK_SIZE = self.SPI_SECTORS_PER_BLOCK * self.SPI_SECTOR_SIZE
                self.SPI_ADDRESS_LENGTH = 4
                self.SPI_USE_3BYTE_CMDS = False

            # elif self.DEVICE_ID == 0x10:
            #     print "Chip type:         MX25L1006E (0x%02x)" % self.DEVICE_ID
            #     self.SPI_BLOCK_COUNT = 2
            #     self.SPI_SECTORS_PER_BLOCK = 16
            #     self.SPI_SECTOR_SIZE = 0x1000
            #     self.SPI_TOTAL_SECTORS = self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT
            #     self.SPI_BLOCK_SIZE = self.SPI_SECTORS_PER_BLOCK * self.SPI_SECTOR_SIZE
            #     self.SPI_ADDRESS_LENGTH = 3
            #     self.SPI_USE_3BYTE_CMDS = False

            else:
                print "Chip type:         Unknown (0x%02x)" % self.DEVICE_ID
                self.close()
                sys.exit(1)

        # elif self.MF_ID == 0xEF:
        #     print "Chip manufacturer: Winbond (0x%02x)"%self.MF_ID
        #     if self.DEVICE_ID == 0x10:
        #         print "Chip type:         W25X10CL (0x%02x)"%self.DEVICE_ID
        #         self.SPI_BLOCK_COUNT = 2
        #         self.SPI_SECTORS_PER_BLOCK = 16
        #         self.SPI_SECTOR_SIZE = 0x1000
        #         self.SPI_TOTAL_SECTORS = self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT
        #         self.SPI_BLOCK_SIZE = self.SPI_SECTORS_PER_BLOCK * self.SPI_SECTOR_SIZE
        #         self.SPI_ADDRESS_LENGTH = 3
        #         self.SPI_USE_3BYTE_CMDS = False
        #     elif self.DEVICE_ID == 0x13:
        #         print "Chip type:         W25Q80BV (0x%02x)"%self.DEVICE_ID
        #         self.SPI_BLOCK_COUNT = 16
        #         self.SPI_SECTORS_PER_BLOCK = 16
        #         self.SPI_SECTOR_SIZE = 0x1000
        #         self.SPI_TOTAL_SECTORS = self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT
        #         self.SPI_BLOCK_SIZE = self.SPI_SECTORS_PER_BLOCK * self.SPI_SECTOR_SIZE
        #         self.SPI_ADDRESS_LENGTH = 3
        #         self.SPI_USE_3BYTE_CMDS = False
        #     elif self.DEVICE_ID == 0x18:
        #         print "Chip type:         W25Q256FV (0x%02x)"%self.DEVICE_ID
        #         self.SPI_BLOCK_COUNT = 512
        #         self.SPI_SECTORS_PER_BLOCK = 16
        #         self.SPI_SECTOR_SIZE = 0x1000
        #         self.SPI_TOTAL_SECTORS = self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT
        #         self.SPI_BLOCK_SIZE = self.SPI_SECTORS_PER_BLOCK * self.SPI_SECTOR_SIZE
        #         self.SPI_ADDRESS_LENGTH = 4
        #         self.SPI_USE_3BYTE_CMDS = True

        #     else:
        #         print "Chip type:         unknown (0x%02x)"%self.DEVICE_ID
        #         self.close()
        #         sys.exit(1)
        else:
            print "Chip manufacturer: Unknown (0x%02x)" % self.MF_ID
            print "Chip type:         Unknown (0x%02x)" % self.DEVICE_ID
            self.close()
            sys.exit(1)

        print
        if (self.SPI_BLOCK_SIZE * self.SPI_BLOCK_COUNT / 1024) <= 8192:
            print "Chip size:         %d KB" % (self.SPI_BLOCK_SIZE * self.SPI_BLOCK_COUNT / 1024)
        else:
            print "Chip size:         %d MB" % (self.SPI_BLOCK_SIZE * self.SPI_BLOCK_COUNT / 1024 / 1024)

        print "Sector size:       %d bytes" % (self.SPI_SECTOR_SIZE)
        print "Block size:        %d bytes" % (self.SPI_BLOCK_SIZE)
        print "Sectors per block: %d" % (self.SPI_SECTORS_PER_BLOCK)
        print "Number of blocks:  %d" % (self.SPI_BLOCK_COUNT)
        print "Number of sectors: %d" % (self.SPI_SECTORS_PER_BLOCK * self.SPI_BLOCK_COUNT)


    # Read a range of blocks (all blocks by default) and save the contents to a file
    # It is STRONGLY RECOMMENDED to dump the ROM multiple times and verify their checksums before trying to flash the chip.
    def dump(self, filename, blockOffset, nblocks):
        fo = open(filename, "wb")

        if nblocks == 0:
            nblocks = self.SPI_BLOCK_COUNT - blockOffset

        if nblocks > self.SPI_BLOCK_COUNT:
            nblocks = self.SPI_BLOCK_COUNT
        
        for block in range(blockOffset, (blockOffset + nblocks), 1):
            data = self.readBlock(block)
            fo.write(data)
            print "\r%d KB / %d KB" % ((block - blockOffset + 1) * self.SPI_BLOCK_SIZE / 1024, nblocks * self.SPI_BLOCK_SIZE / 1024),
            sys.stdout.flush()


    # Programs a range of blocks (all blocks by default), one block at a time.
    def program(self, data, blockOffset, nblocks):
        dataSize = len(data)

        if nblocks == 0:
            nblocks = self.SPI_BLOCK_COUNT - blockOffset
            
        # Validate that the data is a multiplication of self.SPI_BLOCK_SIZE
        if dataSize % self.SPI_BLOCK_SIZE:
            print "Error: expecting file size to be a multiplication of block size: %d" % (self.SPI_BLOCK_SIZE)
            return -1

        # Validate that the the user didn't want to read from incorrect place in the file
        if blockOffset + nblocks > dataSize / self.SPI_BLOCK_SIZE:
            print "Error: file is %d bytes long and last block is at %d!" % (dataSize, (blockOffset + nblocks + 1) * self.SPI_BLOCK_SIZE)
            return -1
        
        # Validate that the the user didn't want to write to incorrect place on the chip
        if blockOffset + nblocks > self.SPI_BLOCK_COUNT:
            print "Error: chip has %d blocks. Block %d is outside the chip's capacity!" % (self.SPI_BLOCK_COUNT, blockOffset + nblocks + 1)
            return -1

        print "Writing %d blocks to device (starting at offset %d)..." % (nblocks, blockOffset)
        
        for block in range(blockOffset, (blockOffset + nblocks), 1):
            if not self.programBlock(data[block * self.SPI_BLOCK_SIZE:(block + 1) * self.SPI_BLOCK_SIZE], block):
                break
            print "\r%d KB / %d KB" % ((block - blockOffset + 1) * self.SPI_BLOCK_SIZE / 1024, nblocks * self.SPI_BLOCK_SIZE / 1024),
            sys.stdout.flush()

        print


def printHelp():
    print "Usage:"
    print "TeensySPIFlasher.py SerialPort Command"
    print
    print "  SerialPort: Name of serial port to open (eg. COM1, COM2, /dev/ttyACM0, etc.)"
    print "  Commands:"
    print "  *  info"
    print "     Displays chip information"
    print "  *  dump Filename [Offset] [Length]"
    print "     Dumps to Filename at [Offset] and [Length]"
    print "  *  vwrite/write Filename [Offset] [Length]"
    print "     Flashes and verifies Filename at [Offset] and [Length]"
    print "     (vwrite and write commands are identical)"
    print "  *  erasechip"
    print "     Erases the entire chip"
    print
    print "     Note: All offsets and lengths are in decimal (number of blocks)."
    print
    print "Examples:"
    print "  TeensySPIFlasher.py COM1 info"
    print "  TeensySPIFlasher.py COM2 dump d:\myflash.bin"
    print "  TeensySPIFlasher.py COM2 dump d:\myflash.bin 10 20"
    print "  TeensySPIFlasher.py COM3 write d:\myflash.bin"
    print "  TeensySPIFlasher.py COM3 write d:\myflash.bin 10 20"
    print "  TeensySPIFlasher.py COM4 vwrite d:\myflash.bin"
    print "  TeensySPIFlasher.py COM4 vwrite d:\myflash.bin 10 20"
    print "  TeensySPIFlasher.py COM500 erasechip"
        

if __name__ == "__main__":
    VERSION_MAJOR = 0
    VERSION_MINOR = 1

    print "TeensySPIFlasher v%d.%02d - Teensy++ 4.1 SPI Flasher for PS4" % (VERSION_MAJOR, VERSION_MINOR)
    print "Copyright (C) 2024 jakatackka@gmail.com"
    print

    if len(sys.argv) in (1, 2) or (len(sys.argv) == 3 and sys.argv[2] == "help"):
        printHelp()
        sys.exit(0)

    n = SPIFlasher(sys.argv[1], VERSION_MAJOR, VERSION_MINOR)
    print "Pinging Teensy..."
    n.ping()
    
    tStart = time.time()
    if len(sys.argv) == 3 and sys.argv[2] == "info":
        n.getSpiInfo()

    elif len(sys.argv) in (4,5,6) and sys.argv[2] == "dump":
        n.getSpiInfo()
        print
        print "Dumping...",
        sys.stdout.flush()
        print
        
        blockOffset = 0
        nblocks = 0

        if len(sys.argv) >= 5:
            blockOffset = int(sys.argv[4])
        if len(sys.argv) == 6:
            nblocks = int(sys.argv[5])

        n.dump(sys.argv[3], blockOffset, nblocks)

    elif len(sys.argv) in (4,5,6) and (sys.argv[2] == "write" or sys.argv[2] == "vwrite"):
        n.getSpiInfo()
        print
        sys.stdout.flush()
        
        data = open(sys.argv[3], "rb").read()

        blockOffset = 0
        nblocks = 0
        
        if len(sys.argv) >= 5:
            blockOffset = int(sys.argv[4])
        if len(sys.argv) == 6:
            nblocks = int(sys.argv[5])

        n.program(data, blockOffset, nblocks)
        
    elif len(sys.argv) == 3 and sys.argv[2] == "erasechip":
        n.getSpiInfo()
        print
        print "Erasing chip (this can take up to 5 minutes)..."
        n.eraseChip()
        
    print
    print "Done. [%s]" % (datetime.timedelta(seconds = time.time() - tStart))
