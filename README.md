
### Warning - this is the first release!  Backup your files before trying this!

## Background ##

**showtool** is used to manipulate Show Tape files. These files originated with the program Reel2Reel and contain information for running animatronic shows.

## Xshw files ##

R2R format files generally have a .Xshw extension, where the X indicates which stage the file is intended for.  The format is a .NET-specific format, using a "no-longer recommended" BinaryFormatter.  It contains an audio wavfile, and a big list of channel activations. 

The list format is a simple, concatenated list of zero-terminated lists, one per each 1/60th of a second frame.  Each frame then, represents the list of channels which are active during that frame.

## Xshz files ##

I have defined an alternative, open format containing the same information.  The preferred extension is .Xshz. This is just a simple zipfile containing the uncompressed wavfile, and a zipped json array containing the channel activations.  Hopefully these files provide a more open format for Showtape archival and exchange.

## Scope ##

In this first release, this tool can check the integrity of .Xshw and .Xshz files, convert them back and forth, and pack/unpack their contents.

## Note ##

**Note - I have a limited number of show files to test with.  Please let me know if you find any bugs or have any suggestions for improvements or new features!**

Thanks!
-Frank

```
usage: showtool [-h]
                (-v | -t [INFILE] | -c INFILE [OUTFILE ...] | -p [OUTFILE] | -u [INFILE])

Showtape Tool - v0.90

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         print version Info
  -t [INFILE], --test [INFILE]
                        test file integrity
  -c INFILE [OUTFILE ...], --convert INFILE [OUTFILE ...]
                        convert file format
  -p [OUTFILE], --pack [OUTFILE]
                        package components into a file
  -u [INFILE], --unpack [INFILE]
                        unpackage file into components

```
