#!/usr/bin/env python3

import sys
import struct
from enum import Enum

ESCAPE = b'\x1b'
UEL_COMMAND = ESCAPE + b'%-12345X'

def get_values(args, num):
    try:
        return args[num]
    except KeyError:
        return num

def get_page_size(num):
    return get_values({
        b'1': 'Executive (7 1/4 x 10 1/2 in.)',
        b'2': 'Letter (8 1/2 x 11 in.)',
        b'3': 'Legal (8 1/2 x 14 in.)',
        b'6': 'Ledger (11 x 17 in.)',
        b'26': 'A4 (210mm x 297mm)',
        b'27': 'A3 (297mm x 420mm)',
        b'80': 'Monarch (Letter - 3 7/8 x 7 1/2 in.)',
        b'81': 'Com-10 (Business - 4 1/8 x 9 1/2 IN.)',
        b'90': 'International DL (110mm x 220mm)',
        b'91': 'International C5 (162mm x 229mm)',
        b'100': 'International B5 (176mm x 250mm)'
    }, num)

def get_paper_source(num):
    return get_values({
        b'0': 'Print the current page',
        b'1': 'Feed the paper from the a printer-specific tray',
        b'2': 'Feed paper from manual input',
        b'3': 'Feed envelope from manual input',
        b'4': 'Feed paper from lower tray',
        b'5': 'Feed from optional paper source',
        b'6': 'Feed envelope from optional envelope. feeder'
    }, num)

def get_page_orientation(num):
    return get_values({
            b'0': 'Portrait',
            b'1': 'Landscape',
            b'2': 'Reverse Portrait',
            b'3': 'Reverse Landscape'
        }, num)

def get_compression_method(num):
    return get_values({
            b'0': 'Unencoded',
            b'1': 'Run-length encoding',
            b'2': 'Tagged Imaged File Format (TIFF) rev. 4.0',
            b'3': 'Delta row compression',
            b'4': 'Reserved',
            b'5': 'Adaptive compression',
        }, num)

class PCLAction:
    def __init__(self, c):
        self.c = c

    def parse(self, f, c):
        return

class TwoCharacterAction(PCLAction):
    characters = {
        b'E': '<RESET>',
        9: '<RESET MARGIN>',
    }

    def __init__(self, c):
        super().__init__(c)

    def parse(self, f, c):
        print(self.characters[self.c])
        return True

class PCLSubAction:
    def __init__(self, f, c):
        self.f = f
        self.c = c
        self.num = b''
        self.cmd = ''
        self.display = True

    def show(self):
        if self.display:
            print(self)

    def read(self):
        num = b''
        self.is_double = False
        is_first = True
        while True:
            c = self.f.read(1)
            if c == b'':
                print("Wrong end")
                break
            elif ord(c) >= 48 and ord(c) <= 57:
                num += c
            elif is_first and (c == b'-' or c == b'+'):
                num += c
            elif not self.is_double and (c == b'.'):
                num += c
                self.is_double = True
            else:
                num = self.read_end(num, c)
                break
            is_first = True
        self.number = num
        return True

    def read_end(self, num, c):
        return num

    def __str__(self):
        return '<{}: {}>'.format(self.cmd, self.number)

    def next_command(self):
        b = self.__class__(self.f, self.c)
        b.read()
        b.show()

class PCLNumber(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f, c)

    def read_end(self, num, c):
        if c.upper() == b'X':
            self.cmd = 'Number of Copies'
        elif c.upper() == b'S':
            if num == b'0':
                self.cmd = 'Simplex'
            elif num == b'1':
                self.cmd = 'Duplex, Long-Edge'
            elif num == b'2':
                self.cmd = 'Duplex, Short-Edge'
            else:
                self.cmd = 'Unkown Simplex/Duplex'
        elif c.upper() == b'U':
            self.cmd = 'Left Offset Registration'
        elif c.upper() == b'Z':
            self.cmd = 'Top Offset Registration'
        elif c.upper() == b'T':
            self.cmd = 'Job Seperation'
        elif c.upper() == b'G':
            self.cmd = 'Output Bin'
        elif c.upper() == b'A':
            self.cmd = 'Page Size'
            num = get_page_size(num)
        elif c.upper() == b'H':
            self.cmd = 'Paper Source'
            num = get_page_source(num)
        elif c.upper() == b'O':
            self.cmd = 'Logical Page Orientation'
            num = get_page_orientation(num)
        elif c.upper() == b'E':
            self.cmd = 'Top Margin'
        elif c.upper() == b'F':
            self.cmd = 'Text Length'
        elif c.upper() == b'C':
            self.cmd = 'Vertical Motion Index'
        elif c.upper() == b'D':
            self.cmd = 'Line Spacing'
        elif c.upper() == b'L':
            self.cmd = 'Performation skip'
        else:
            print("Error: Number: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'
        if c.islower():
            self.next_command()

        return num

class PCLRaster2(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f, c)
    def read_end(self, num, c):
        if c.upper() == b'R':
            self.cmd = 'Dots per inch'
        else:
            print("Error: Raster 2: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'
        if c.islower():
            self.next_command()

        return num
class PCLRasterGraphics(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f, c)

    def read_end(self, num, c):
        if c.upper() == b'T':
            self.cmd = 'Raster Height'
        elif c.upper() == b'S':
            self.cmd = 'Raster Width'
        elif c.upper() == b'A':
            self.cmd = 'Start Raster Graphics'
            if num == b'0':
                num = 'Start graphics at default left graphics margin'
            elif num == b'1':
                num = 'Start graphics at current cursor position (current X-position)'
        elif c.upper() == b'B':
            self.cmd = 'Old End Raster Graphics'
        elif c.upper() == b'C':
            self.cmd = 'End Raster Graphics'
        elif c.upper() == b'F':
            self.cmd = 'Raster Graphics Representation'
            if num == b'0':
                num = 'Raster image prints in orientation of logical page'
            elif num == b'3':
                num = 'Raster image prints along the width of the physical page'
        else:
            print("Error: Raster: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'

        if c.islower():
            self.next_command()
        return num

class PCLCursorPositioning(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f,c)

    def read_end(self, num, c):
        if c.upper() == b'X':
            self.cmd = 'Horizontal Cursor Positioning'
        elif c.upper() == b'Y':
            self.cmd = 'Number of PCL Units'
        elif c.upper() == b'R':
            self.cmd = 'Set Pattern Reference'
            if num == b'0':
                num = 'Rotate patterns with print direction'
            elif num == b'1':
                num = 'Keep patterns fixed'
        else:
            print("Error: Cursor: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'

        if c.islower():
            self.next_command()
        return num

class PCLUnitMeasure(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f, c)
    def read_end(self, num, c):
        if c.upper() == b'D':
            self.cmd = 'Number of units per inch'
        else:
            print("Error: UnitMeasure: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'


        if c.islower():
            self.next_command()
        return num


def skip_data(f, num):
    f.read(num)

class PCLRasterOffset(PCLSubAction):
    def __init__(self, f, c):
        super().__init__(f, c)
    def read_end(self, num, c):
        if c.upper() == b'Y':
            self.cmd = 'Number of raster lines of vertical movement'
        elif c.upper() == b'M':
            self.cmd = 'Set Compression Method'
            num = get_compression_method(num)
        elif c.upper() == b'W':
            self.cmd = 'Raster data (skipped)'
            skip_data(self.f, int(num))
            self.display = False
        else:
            print("Error: RasterOffset: Unkown character: {} ({})".format(c, num))
            self.cmd = 'Unkown'

        if c.islower():
            self.next_command()
        return num
class ParameterizedAction(PCLAction):
    characters = {
        b'&l': PCLNumber,
        b'*r': PCLRasterGraphics,
        b'&u': PCLUnitMeasure,
        b'*p': PCLCursorPositioning,
        b'*t': PCLRaster2,
        b'*b': PCLRasterOffset,
    }

    def __init__(self, c):
        super().__init__(c)

    def set_group(self, c):
        if self.is_termination(c):
            return True
        if ord(c) >= 48 and ord(c) <= 57:
            self.group = c
            return True
        return False

    def get_value(f):
        return

    def set_parameter(c):
        if self.is_termination(c):
            return True
        if ord(c) >= 96 and ord(c) <= 126:
            self.param = c
            return True
        return False

    def is_termination(self, c):
        return ord(c) >= 64 and ord(c) <= 94

    def parse(self, f, c):
        c2 = f.read(1)
        if c == b'':
            return False
        try:
            s = self.characters[c + c2](f, c + c2)
            s.read()
            s.show()
        except KeyError as err:
            print("Error: {}".format(err))
            return False

        return True

def get_action(c):
    o = ord(c)
    if o >= 48 and o <= 126:
        return TwoCharacterAction(c)
    elif o >= 33 and o <= 47:
        return ParameterizedAction(PCLAction)
    else:
        return None

def handle_escape(f):
    c = f.read(1)
    if c == b'':
        return False
    n = get_action(c)
    if n is None:
        print('Error: Unkown character: {}'.format(c))
        return False
    n.parse(f, c)

    return True

def read_metadata(f):
    while True:
        c = f.read(1)
        if c == b'':
            break
        elif c == b'\x0c' or c == b'\x0a':
            continue
        elif c != ESCAPE:
            print('not <ESC> ({})'.format(c))
            continue
        if not handle_escape(f):
            break

def main(args):
    if len(args) < 2:
        print('Need a filename.')
        return

    with open(args[1], 'rb') as f:
        print('read file: {}'.format(args[1]))
        read_metadata(f)


if __name__ == '__main__':
    main(sys.argv)
