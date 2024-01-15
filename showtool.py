
# Tool for Manipulating Showtape Files
# Frank Palazzolo - github.com/palazzol
version_str = '0.91'

import sys
import struct
import json
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
import wave
import io
import argparse
from pathlib import Path
#import filecmp

'''
TODO:
validate wav file params better?
validate stages?
'''

header = b'\x00\x01\x00\x00\x00\xff\xff\xff\xff\x01\x00\x00\x00\x00\x00\x00\x00\x0c\x02\x00\x00\x00FAssembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null\x05\x01\x00\x00\x00\nrshwFormat\x03\x00\x00\x00\x1a<audioData>k__BackingField\x1b<signalData>k__BackingField\x1a<videoData>k__BackingField\x07\x07\x07\x02\x08\x02\x02\x00\x00\x00\t\x03\x00\x00\x00\t\x04\x00\x00\x00\n\x0f\x03\x00\x00\x00'
footer = b'\x0bv1.4,App=shw_to_rshw,ShwFps=40,Map=DefaultNonLinear\x00'

def validateLength(chunk, length):
    if len(chunk) != length:
        print("Error: Format invalid!")
        sys.exit(-1)

def validateContent(chunk, reference):
    if chunk != reference:
        print("Error: Format invalid!")
        sys.exit(-1)

def readShwFile(infilename):
    # Validate format and extract data
    p = Path(infilename)
    if not p.is_file():
        print(f"Error: File {infilename} doesn't exist")
        sys.exit(-1)
    print(f"Reading {infilename}...")
    with p.open('rb') as f:
        chunk = f.read(0xdd)
        validateLength(chunk, 0xdd)
        validateContent(chunk, header)
        chunk = f.read(0x05)
        validateLength(chunk, 0x05)
        s = struct.unpack('=1i1b', chunk)
        validateContent(s[1], 0x02)
        wavfilelength = s[0]
        #print(wavfilelength)
        audioData = f.read(wavfilelength)
        chunk = f.read(5)
        validateContent(chunk, b'\x0f\x04\x00\x00\x00')
        chunk = f.read(5)
        validateLength(chunk, 0x05)
        s = struct.unpack('=1i1b', chunk)
        validateContent(s[1], 0x08)
        signalfilesamples = s[0]
        #print(signalfilesamples)
        chunk = f.read(signalfilesamples*4)
        signalData = struct.unpack(f'={signalfilesamples}i',chunk)
        chunk = f.read(1)
        validateContent(chunk, b'\x0b') # MessageEnd Record
        footer = f.read()
        #print("File Format OK")
        videxists = False
        if infilename[-4] in 'rRsS':
            vidfilename = infilename[:-5] + '.mp4'
            p = Path(vidfilename)
            if p.is_file():
                videxists = True
        return audioData, signalData, footer, videxists

def readRawFiles():
    p = Path('audioData.wav')
    if not p.is_file():
        print(f"Error: File audioData.wav doesn't exist")
        sys.exit(-1)
    print(f"Reading audioData.wav...")
    with p.open('rb') as f:
        audioData = f.read()
    p = Path('signalData.json')
    if not p.is_file():
        print(f"Error: File signalData.json doesn't exist")
        sys.exit(-1)        
    print(f"Reading signalData.json...")
    with p.open('r') as f:
        signalDataJson = f.read()
    signalData = json.loads(signalDataJson)
    return audioData, signalData

def writeRawFiles(audioData, signalData):
    # Write individual files
    p = Path('audioData.wav')
    if p.is_file():
        print("Error: File audioData.wav already exists")
        sys.exit(-1)
    print(f"Writing {'audioData.wav'}...")
    with p.open('wb') as f:
        f.write(audioData)
    p = Path('signalData.json')
    if p.is_file():
        print("Error: File signalData.json already exists")
        sys.exit(-1)        
    print(f"Writing {'signalData.json'}...")
    with p.open('w') as f:
        json.dump(signalData, f)

def writeShzFile(outfilename, audioData, signalData):
    p = Path(outfilename)
    if p.is_file():
        print(f"Error: File {outfilename} already exists")
        sys.exit(-1)
    print(f"Writing {outfilename}...")
    audioDataBuffer = io.BytesIO(audioData)
    signalDataBuffer = io.BytesIO()
    with ZipFile(signalDataBuffer,'w',ZIP_DEFLATED) as f:
        f.writestr('signalData.json',json.dumps(signalData))
    with ZipFile(outfilename,'w',ZIP_STORED) as f:
        f.writestr('audioData.wav', audioDataBuffer.getvalue())
        f.writestr('signalData.zip',signalDataBuffer.getvalue())

def readShzFile(infilename):
    p = Path(infilename)
    if not p.is_file():
        print(f"Error: File {infilename} doesn't exist")
        sys.exit(-1)
    print(f"Reading {infilename}...")
    with ZipFile(infilename,'r') as f:
        with f.open('audioData.wav','r') as f2:
            audioData = f2.read()
        with f.open('signalData.zip','r') as f2:
            signalDataZip = f2.read()
    signalDataBuffer = io.BytesIO(signalDataZip)
    with ZipFile(signalDataBuffer,'r',ZIP_DEFLATED) as f:
        signalDataJson = f.read('signalData.json')
    signalData = json.loads(signalDataJson)
    return audioData, signalData

def writeShwFile(outfilename, audioData, signalData):
    p = Path(outfilename)
    if p.is_file():
        print(f"Error: File {outfilename} already exists")
        sys.exit(-1)
    print(f"Writing {outfilename}...")
    with open(outfilename,'wb') as f:
        f.write(header)
        chunk = struct.pack('=1i1b', len(audioData), 0x02 )
        f.write(chunk)
        f.write(audioData)
        f.write(b'\x0f\x04\x00\x00\x00')
        signalfilesamples = len(signalData)
        #print(signalfilesamples)
        chunk = struct.pack('=1i1b', signalfilesamples, 0x08)
        f.write(chunk)
        chunk = struct.pack(f'={signalfilesamples}i', *signalData)
        f.write(chunk)
        f.write(footer)

def validateWavFile(audioData):
    if audioData[0:4] != b'RIFF':
        print("Error: audioData is not a RIFF file!")
        sys.exit(-1)
    audioDataSize = len(audioData)
    cs = struct.unpack('=i',audioData[4:8])[0]
    if cs+8 != audioDataSize:
        print("Warning: RIFF chunk size incorrect, will auto-repair if written")
        chunk = struct.pack('=i',audioDataSize-8)
        audioData = bytearray(audioData)
        audioData[4:8] = chunk
        audioData = bytes(audioData)
    return audioData

def printStats(infilename, audioData, signalData, footer, videxists):
    audioDataBuffer = io.BytesIO(audioData)
    with wave.open(audioDataBuffer,'rb') as f:
        print( "Audio Info:")
        print( "    Number of channels:",f.getnchannels())
        print( "    Sample width       ",f.getsampwidth())
        print( "    Frame rate:        ",f.getframerate())
        print( "    Number of frames:  ",f.getnframes())
        print( "    Duration (s):      ",f.getnframes()/f.getframerate())
        #print ( "parameters:",f.getparams())
    m = 0
    c = 0
    for v in signalData:
        if v == 0:
            c += 1
        if v > m:
            m = v
    print( "Signal Info: ")
    print( "    Number of frames:  ",c)
    print( "    Max channel number:",m)
    print( "    Duration (s):      ",c/60.0)
    print( "Footer Info: ")
    print(f"    {footer}")
    if infilename[-4] in 'rRsS':
        if videxists:
            print( "Matching mp4 file exists" )
        else:
            print( "Matching mp4 file missing" )
    print()


def convertToShz(infilename, outfilename=''):
    # Validate format and extract data
    audioData, signalData, footer, videxists = readShwFile(infilename)
    audioData = validateWavFile(audioData)
    # Write outfile
    if outfilename == '':
        outfilename = infilename[:-1]+'z'
    writeShzFile(outfilename, audioData, signalData)
    print('Done.')

def convertToShw(infilename, outfilename=''):
    audioData, signalData = readShzFile(infilename)
    audioData = validateWavFile(audioData)
    if outfilename == '':
        outfilename = infilename[:-1]+'w'
    writeShwFile(outfilename,audioData,signalData)
    print('Done.')

def unpackFromShz(infilename):
    audioData, signalData = readShzFile(infilename)
    audioData = validateWavFile(audioData)
    writeRawFiles(audioData, signalData)
    print('Done.')

def unpackFromShw(infilename):
    audioData, signalData, footer, videxists = readShwFile(infilename)
    audioData = validateWavFile(audioData)
    writeRawFiles(audioData, signalData)
    print('Done.')

def packToShz(outfilename):
    audioData, signalData = readRawFiles()
    audioData = validateWavFile(audioData)
    writeShzFile(outfilename, audioData, signalData)
    print('Done.')

def packToShw(outfilename):
    audioData, signalData = readRawFiles()
    audioData = validateWavFile(audioData)
    writeShwFile(outfilename, audioData, signalData)
    print('Done.')

def testShwFile(infilename):
    audioData, signalData, footer, videxists = readShwFile(infilename)
    audioData = validateWavFile(audioData)
    printStats(infilename, audioData, signalData, footer, videxists)

def testShzFile(infilename):
    audioData, signalData = readShzFile(infilename)
    audioData = validateWavFile(audioData)
    printStats(infilename, audioData, signalData, '', False)

def getFileTypeFromName(filename):
    if len(filename) < 6:
        return ''
    if filename[-5] == '.' and filename[-3:] == 'shw':
        return filename[-4:]
    if filename[-5] == '.' and filename[-3:] == 'shz':
        return filename[-4:]

'''
def fileCompare(f1, f2):
    print(f'Comparing {f1} and {f2}...',end='')
    if filecmp.cmp(f1,f2):
        print('GOOD')
    else:
        print('BAD!')
        sys.exit(-1)

def test(shwfilename):
    convertToShz(shwfilename)
    shzfilename = shwfilename[:-1]+'z'
    shw2filename = shwfilename[:-5]+'2' + shwfilename[-5:]
    convertToShw(shzfilename,shw2filename)
    fileCompare(shwfilename,shw2filename)
    print()
'''

def main():
    # Parsing the arguments
    parser = argparse.ArgumentParser(description = f'Showtape Tool - v{version_str}')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-v','--version',help='print version Info',required=False,action="store_true")
    group.add_argument('-t','--test',help='test file integrity',nargs='?',metavar='INFILE',required=False)
    group.add_argument('-c','--convert',help='convert file format',nargs='+',metavar=('INFILE','OUTFILE'),required=False)
    group.add_argument('-p','--pack',help='package components into a file',nargs='?',metavar='OUTFILE',required=False)
    group.add_argument('-u','--unpack',help='unpackage file into components',nargs='?',metavar='INFILE',required=False)
    global_args = parser.parse_args()

    if global_args.version:
        print(f'{sys.argv[0]} - v{version_str}')
    if global_args.test:
        t = getFileTypeFromName(global_args.test)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            testShwFile(global_args.test)
        if t[-1] == 'z':
            testShzFile(global_args.test)
    if global_args.convert:
        infilename = global_args.convert[0]
        if len(global_args.convert) > 1:
            outfilename = global_args.convert[1]
        else:
            outfilename = ''
        t = getFileTypeFromName(infilename)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            convertToShz(infilename, outfilename)
        if t[-1] == 'z':
            convertToShw(infilename, outfilename)
    if global_args.unpack:
        t = getFileTypeFromName(global_args.unpack)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            unpackFromShw(global_args.unpack)
        if t[-1] == 'z':
            unpackFromShz(global_args.unpack)
    if global_args.pack:
        t = getFileTypeFromName(global_args.pack)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            packToShw(global_args.pack)
        if t[-1] == 'z':
            packToShz(global_args.pack)

if __name__ == "__main__":
    main()
