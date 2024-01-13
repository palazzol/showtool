import sys
import struct
import json
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
import filecmp
import wave
import io
import argparse

'''
TODO:
dont clobber existing files by default!!!
verify/use unsigned ints for lengths of files
validate wav files params better
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
    print(f"Reading {infilename}...")
    with open(infilename,'rb') as f:
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
        chunk = f.read(53)
        validateContent(chunk, footer)
        chunk = f.read(1)
        validateLength(chunk,0)
        #print("File Format OK")
        return audioData, signalData

def readRawFiles():
    print(f"Reading {'audioData.wav'}...")
    with open('audioData.wav','rb') as f:
        audioData = f.read()
    print(f"Reading {'signalData.json'}...")
    with open('signalData.json','r') as f:
        signalDataJson = f.read()
    signalData = json.loads(signalDataJson)
    return audioData, signalData

def writeRawFiles(audioData, signalData):
    # Write individual files
    print(f"Writing {'audioData.wav'}...")
    with open('audioData.wav','wb') as f:
        f.write(audioData)
    print(f"Writing {'signalData.json'}...")
    with open('signalData.json','w') as f:
        json.dump(signalData, f)

def writeShzFile(outfilename, audioData, signalData):
    print(f"Writing {outfilename}...")
    audioDataBuffer = io.BytesIO(audioData)
    signalDataBuffer = io.BytesIO()
    with ZipFile(signalDataBuffer,'w',ZIP_DEFLATED) as f:
        f.writestr('signalData.json',json.dumps(signalData))
    with ZipFile(outfilename,'w',ZIP_STORED) as f:
        f.writestr('audioData.wav', audioDataBuffer.getvalue())
        f.writestr('signalData.zip',signalDataBuffer.getvalue())

def readShzFile(infilename):
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

def printStats(audioData, signalData):
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

def convertToShz(infilename, outfilename=''):
    # Validate format and extract data
    audioData, signalData = readShwFile(infilename)
    # Write outfile
    if outfilename == '':
        outfilename = infilename[:-1]+'z'
    writeShzFile(outfilename, audioData, signalData)

def convertToShw(infilename, outfilename=''):
    audioData, signalData = readShzFile(infilename)
    if outfilename == '':
        outfilename = infilename[:-1]+'w'
    writeShwFile(outfilename,audioData,signalData)

def unpackFromShz(infilename):
    audioData, signalData = readShzFile(infilename)
    writeRawFiles(audioData, signalData)

def unpackFromShw(infilename):
    audioData, signalData = readShwFile(infilename)
    writeRawFiles(audioData, signalData)

def packToShz(outfilename):
    audioData, signalData = readRawFiles()
    writeShzFile(outfilename, audioData, signalData)

def packToShw(outfilename):
    audioData, signalData = readRawFiles()
    writeShwFile(outfilename, audioData, signalData)

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

def testShwFile(infilename):
    audioData, signalData = readShwFile(infilename)
    printStats(audioData, signalData)

def testShzFile(infilename):
    audioData, signalData = readShzFile(infilename)
    printStats(audioData, signalData)

def getFileTypeFromName(filename):
    if len(filename) < 6:
        return ''
    if filename[-5] == '.' and filename[-3:] == 'shw':
        return filename[-4:]
    if filename[-5] == '.' and filename[-3:] == 'shz':
        return filename[-4:]

def main():
    # Parsing the arguments
    parser = argparse.ArgumentParser(description = 'Showfile Tool')
    parser.add_argument('-v','--version',help='Print Version Info',required=False,action="store_true")
    parser.add_argument('-t','--test',help='Test File Integrity',required=False,action="store_true")
    parser.add_argument('-c','--convert',help='Convert File Formats',required=False,action="store_true")
    parser.add_argument('-p','--pack',help='Package components into a file',required=False,action="store_true")
    parser.add_argument('-u','--unpack',help='Unpackage file into components',required=False,action="store_true")
    parser.add_argument('infile', nargs='?',type=str)
    parser.add_argument('outfile', nargs='?',type=str)
    global_args = parser.parse_args()

    if global_args.version:
        print(f'{sys.argv[0]} - v1.0')
        sys.exit(0)
    if global_args.test:
        if not global_args.infile:
            print('Error: infile argument required')
            sys.exit(-1)
        t = getFileTypeFromName(global_args.infile)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            testShwFile(global_args.infile)
            sys.exit(0)
        if t[-1] == 'z':
            testShzFile(global_args.infile)
            sys.exit(0)
    if global_args.convert:
        if not global_args.infile:
            print('Error: infile argument required')
            sys.exit(-1)
        if not global_args.outfile:
            global_args.outfile = ''
        t = getFileTypeFromName(global_args.infile)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            convertToShz(global_args.infile, global_args.outfile)
            sys.exit(0)
        if t[-1] == 'z':
            convertToShw(global_args.infile, global_args.outfile)
            sys.exit(0)
    if global_args.unpack:
        if not global_args.infile:
            print('Error: infile argument required')
            sys.exit(-1)
        t = getFileTypeFromName(global_args.infile)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            unpackFromShw(global_args.infile)
            sys.exit(0)
        if t[-1] == 'z':
            unpackFromShz(global_args.infile)
            sys.exit(0)
    if global_args.pack:
        if not global_args.infile:
            print('Error: infile argument required')
            sys.exit(-1)
        t = getFileTypeFromName(global_args.infile)
        if t == '':
            print('Error: Cannot guess filetype from file extension')
            sys.exit(-1)
        if t[-1] == 'w':
            packToShw(global_args.infile)
            sys.exit(0)
        if t[-1] == 'z':
            packToShz(global_args.infile)
            sys.exit(0)
    print('Error: Must have at least one argument, type "showtool -h" for more info')
    sys.exit(-1)

if __name__ == "__main__":
    main()
