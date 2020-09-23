'''Utilities for reading input data for time-series InSAR analysis.

.. author:

    Piyush Agram <piyush@gps.caltech.edu>
    
.. Dependencies:

    numpy, h5py, time, logging
    
.. Comments:
    
    Pylint checked.'''
    
import numpy as np
import h5py
import time
import sys
import logging
import re
import os
import collections
import lxml.objectify as ob


###############################File I/O Utils ############################
def fopen(fname,ext=None,mode='r'):
    '''Searches for file with extensions first. If searching for file with extension .rsc it first searches for file.rsc, if doesnt exist it return handle for file.

    Args:

        * file      -> File basename

    Kwargs:

        * ext       -> Extension to search for. Default: No extension
        * mode      -> Mode to open the file in. Default: r 
        
    Returns:
        
        * fid       -> Pointer to the open file'''
    if ext is not None:
        fin = ''.join((fname,ext))
        if os.path.exists(fin):
            fid = open(fin,mode=mode)
            return fid

    fid = open(fname, mode=mode)
    return fid

#######Grep a file with given pattern
def grep(patt, file):
    '''Greps for a pattern in the given file.

    Args:

        * patt  -> can be any valid regular expression pattern.
        * file  -> File name 

    Returns:

        * res   -> List of lines with the given pattern'''
    res = []
    lineno = 0
    fobj = open(file,'r')
    for line in fobj:
        lineno += 1
        if re.search(patt,line):
            res.append(line)

    return res


###Create a memory map using numpy's memmap module.
def load_mmap(fname, nxx, nyy, map='BSQ', nchannels=1, channel=1, datatype=np.float32, quiet=False, conv=False):
    '''Create a memory map to data on file.

    Args:

        * fname   -> File name
        * nxx     -> Width
        * nyy     -> length

    KwArgs:
        * map       -> Can be 'BIL', 'BIP', 'BSQ' 
        * nchannels -> Number of channels in the BIL file. 
        * channel   -> The channel needed in the multi-channel file
        * datatype  -> Datatype of data in file
        * quiet     -> Suppress logging outputs
        * conv      -> Switch endian

    Returns:

        * fmap     -> The memory map.'''

    if quiet==False:
        logging.info('Reading input file: %s'%(fname))

    ####Get size in bytes of datatype
    ftemp = np.zeros(1, dtype=datatype)
    fsize = ftemp.itemsize

    if map.upper() == 'BIL':  #Band Interleaved by Line 
        nshape = (nchannels*nyy-channel+1, nxx) 
        noffset = (channel-1)*nxx*fsize

        try:
            omap = np.memmap(fname, dtype=datatype, mode='r', shape=nshape, offset = noffset)
        except:
            raise Exception('Could not open BIL style file or file of wrong size: ' + fname)

        if conv:
            gmap = omap.byteswap(False)
        else:
            gmap = omap

        nstrides = (nchannels*nxx*fsize, fsize)

        fmap = np.lib.stride_tricks.as_strided(gmap, shape=(nyy,nxx), strides=nstrides)

    elif map.upper() == 'BSQ': #Band Sequential
        noffset = (channel-1)*nxx*fsize*nyy
        try:
            gmap = np.memmap(fname, dtype=datatype, mode='r', shape=(nyy,nxx), offset=noffset)
        except:
            raise Exception('Could not open BSQ style file or file of wrong size: ' + fname)

        if conv:
            fmap = gmap.byteswap(False)
        else:
            fmap = gmap

    elif map.upper() == 'BIP': #Band interleaved by pixel
        nsamps = nchannels * nyy * nxx  - (channel-1)
        noffset = (channel-1)*fsize

        try:
            gmap = np.memmap(fname, dtype=datatype,mode='r', shape = (nsamps), offset = noffset)
        except:
            raise Exception('Could not open BIP style file or file of wrong size: ' + fname)

        if conv:
            omap = gmap.byteswap(False)
        else:
            omap = gmap

        nstrides = (nchannels*nxx*fsize, nchannels*fsize)
        fmap = np.lib.stride_tricks.as_strided(omap, shape=(nyy,nxx), strides=nstrides)

    return fmap

#####Load the 2 channels of an RMG file.
def load_rmg(fname, nxx, nyy, scale=1.0, datatype=np.float32, quiet=False, conv=False):
    '''Load an RMG file.
    
    Args:
    
        * fname     ->   Name of the file
        * nxx       ->   Width of the image
        * nyy       ->   Length of the image
        
    Kwargs:
    
        * scale     ->   Scales phase by the this factor.
        * datatype  ->   Numpy datatype, FLOAT32 by default.
        
    Returns:
        * phs       ->   Unwrapped phase (Channel 2)
        * mag       ->   Magnitude (Channel 1)'''

    if quiet == False:
        logging.info('READING RMG FILE: %s'%(fname))

    try:
        fin = open(fname, 'rb') #Open in Binary format
        inp = np.fromfile(file=fin, dtype=datatype, count=2 * nxx * nyy)
    except:
        raise Exception('Could not open RMG file or file of wrong size: ' + fname)

    fin.close()

    if conv:
        inp.byteswap(True)

    inp = np.reshape(inp, (nyy, 2*nxx))
    amp = inp[:,0:nxx].copy() #1st line is amplitude
    phs = inp[:, nxx:].copy()        #2nd line is phase
    phs = phs * scale
    phs[phs == 0] = np.NaN
    amp[phs == 0] = np.NaN
    return amp,phs

#####Load a simple float file
def load_flt(fname, nxx, nyy, scale=1.0, datatype=np.float32, quiet=False, conv=False):
    '''Load a FLAT BINARY file.
    
    Args:
    
        * fname         Name of the file
        * nxx           Width of the image
        * nyy           Length of the image
        
    Kwargs:
    
        * scale        Scales by the this factor.
        * datatype     Numpy datatype, FLOAT32 by default.
    
    Returns:
    
        * phs          Scaled array (single channel)'''

    if quiet == False:
        logging.info('READING FLOAT FILE: %s'%(fname))

    phs = np.zeros(nxx * nyy, dtype=datatype)
    try:
        fin = open(fname, 'rb') #Open in Binary format
        phs = np.fromfile(file=fin, dtype=datatype, count=nxx * nyy)
    except:
        raise Exception('Could not open RMG file or file of wrong size: ' + fname)

    fin.close()

    if conv:
        phs.byteswap(True)

    phs = np.reshape(phs, (nyy, nxx))
    phs = phs * scale
    return phs


#######Load a GMT grd file
def load_grd(fname, var='z', shape=None):
    '''Load a GMT grd file.

    Args:

        * fname         Name of the file

    Kwargs:

        * var           Variable name to be loaded, not currently used


    Returns:

        * data          2D array of the data'''

    try:
        import gdal
        from gdalconst import GA_ReadOnly 
    except ImportError:
        raise Exception('GDAL python bindings must be installed for GMTSAR support')

    gdal.UseExceptions()
    try:
        dataset = gdal.Open(fname, GA_ReadOnly )
    except RuntimeError as e:
        print(('Error: GDAL library failed to open GMT file: ' + fname))
        print(e)
        sys.exit(1)

    #print 'Size is ',dataset.RasterXSize,'x',dataset.RasterYSize, 'x',dataset.RasterCount

    #here we should get the band name instead of just assuming band #1
    band = dataset.GetRasterBand(1)

    #read the data
    data=band.ReadAsArray()

    #close the dataset
    dataset = None

    return data

#def load_grd(fname, var='z', shape=None):
#    '''Load a GMT grd file.
#
#    Args:
#
#        * fname         Name of the file
#
#    Kwargs:
#
#        * var           Variable name to be loaded
#
#
#    Returns:
#
#        * data          2D array of the data'''
#
#    print('reading file ' + fname)
#
#    try:
#        fin = netcdf.netcdf_file(fname)
#    except:
#        raise Exception('Could not open GMT file: ' + fname)
#
#    z = fin.variables[var]
#
#    print len(z.shape)
#    print z.shape
#    print shape
#    print z.shape == shape
#
#
#    ####If old format
#    if len(z.shape) == 1:
#        xlims = fin.variables['x_range'].data[:]
#        ylims = fin.variables['y_range'].data[:]
#        spacing = fin.variables['spacing'].data[:]
#
#        xsize =int(np.round(np.abs( (xlims[1] - xlims[0]) / (1.0 * spacing[0]))))
#        ysize = int(np.round(np.abs((ylims[1] - ylims[0]) / (1.0 * spacing[1]))))
#
#        zshape = (ysize,xsize)
#
#        if shape is not None:
#            if zshape != shape:
#                raise ValueError('Shape mismatch in GRD file: '%fname)
#   
#        data = z.data.copy().reshape(zshape)
#        xlims = None
#        ylims = None
#        spacing = None
#        z = None
#
#    ###COARDS compliant format
#    elif len(z.shape) == 2:
#        if shape is not None:
#            if z.shape != shape:
#                raise ValueError('Shape mismatch in GRD file: '%fname)
#
#        data = z.data.copy()
#        z = None
#    else:
#        raise Exception("This GRD file appears to be in a format that GIAnT doesn't quite understand yet. Post to forums with output of 'ncdump -h %s'"%(fname))
#
#
#    fin.close()
#    return data

def textread(fname, strfmt,delim=['#']):
    '''A generic interferogram file list reader. All the possible keywords
    are specified below in defns. Arrays are returned in the same order as 
    specified in the strfmt list. All lines starting with delim are ignored.
    
    'S'  - String
    'I'  - Integer
    'F'  - Float
    'K'  - Skip
    
    Returns:
        
        A tuple of list objects for each of the types requested by the user.'''
        
    inplist = strfmt.split()
    nval = len(inplist)
    
    ########Initiate empty lists
    for ind, inp in enumerate(inplist):
        if inp.upper() not in ('K', 'F', 'I', 'S'):
            raise ValueError('Undefined data type in textread.')
        
        if inp not in ('K', 'k'):
            sname = 'var%2d'% (ind)
            vars()[sname] = []
    
    fin = open(fname, 'r')
    for line in fin.readlines():
        if line[0] not in delim:
            strs = line.split()
            if len(strs) != nval:
                raise ValueError('Number of records does not match strfmt')
        
            for ind, val in enumerate(strs):
                inp = inplist[ind]
                if inp not in ('K', 'k'):
                    sname = 'var%2d'% (ind)
                    vars()[sname].append(val)
        
    fin.close()

    for ind, inp in enumerate(inplist):
        if inp not in ('K', 'k'):
            sname = 'var%2d'% (ind)
            vars()[sname] = np.array(vars()[sname])
            if inp in ('F', 'f'):
                vars()[sname] = vars()[sname].astype(np.float)
            elif inp in ('I', 'i'):
                vars()[sname] = vars()[sname].astype(np.int)
            
    retlist = []
    for ind, inp in enumerate(inplist):
        if inp not in ('K', 'k'):
            sname = 'var%2d'% (ind)
            retlist.append(vars()[sname])
    
    return retlist



#######Read ROI-PAC RSC FILE
def read_rsc(inname):
    '''Reading a ROI-PAC style RSC file.

    Args:
    
        * inname (str): Path to the RSC file.

    Returns:
    
        * rdict (dict): Dictionaty of values in RSC file.
    '''

    logging.info("PROGRESS: READING %s RSC FILE"%(inname))

#    rpacdict = {}
    rpacdict = collections.OrderedDict()
    infile = fopen(inname, ext='.rsc', mode='r')
    line = infile.readline()
    while line:
        llist = line.split()
        if len(llist)==2 :
            rpacdict[llist[0]] = llist[1]
        line = infile.readline()
    infile.close()

    return rpacdict

##########Write ROI-PAC RSC FILE
def write_rsc(rdict, fname):
    '''Writing a ROI-PAC style RSC file from a dictionary.

    Args:
    
        * rdict   (dict): dictionary of values.
        * fname   (str) : output RSC file.

    Returns:
        None'''

    fout = open(fname, 'w')
    for kk in list(rdict.keys()):
        fout.write('{0:<35} \t\t {1:<20}\n'.format(kk, str(rdict[kk])))
    fout.close()

########Read GMTSAR PRM file
def read_prm(inname):
    '''Reading a GMTSAR style PRM file.

    Args:
    
        * inname (str): Path to the PRM file.

    Returns:
    
        * rdict (dict): Dictionaty of values in PRM file.
    '''

    logging.info("PROGRESS: READING %s PRM FILE"%(inname))

    rdict = {}
    infile = fopen(inname, ext='.PRM', mode='r')
    line = infile.readline()
    while line:
        llist = line.split()
        if len(llist)>0 :
            rdict[llist[0]] = llist[-1]
        line = infile.readline()
    infile.close()

    return rdict


def get_grddims(fname, var='z'):
    '''Get the dimensions of the given variable from a GMT file.

    Args:

        * fname (str): GRD file name.

    Kwargs:

        * var : Variable name. Default: 'z'

    Returns:

        * dims  : Dimensions of the array'''

    try:
        import gdal
        from gdalconst import GA_ReadOnly 
    except ImportError:
        raise Exception('GDAL python bindings must be installed for GMTSAR support')

    gdal.UseExceptions()
    try:
        dataset = gdal.Open(fname, GA_ReadOnly )
    except RuntimeError as e:
        print(('Error: GDAL library failed to open GMT file: ' + fname))
        print(e)
        sys.exit(1)

    res=(dataset.RasterYSize,dataset.RasterXSize)

    #close the dataset
    dataset = None

    return res

## old version using NetCDF library
#def get_grddims(fname, var='z'):
#    '''Get the dimensions of the given variable from a GMT file.
#
#    Args:
#
#        * fname (str): GRD file name.
#
#    Kwargs:
#
#        * var : Variable name. Default: 'z'
#
#    Returns:
#
#        * dims  : Dimensions of the array'''
#
#    fin = netcdf.netcdf_file(fname)
#    val = fin.variables[var]
#    res = val.shape
#    fin.close()
#    return res

##########Read ISCE XML file
def read_isce_xml(fname,kwd='property'):
    '''Reads an ISCE style output xml file.

    Args:

        * fname     -> Name of the input XML file
    
    Kwargs:

        * kwd       -> Keyword used to label properties in the xml file.

    Returns:

        * rdict     -> Dictionary of property values'''

    fin = fopen(fname, ext='.xml', mode='r')
    inp = ob.fromstring(fin.read())
    fin.close()

    return inp


##########Read GAMMA par file
def read_par(fname):
    '''Reads a gamma parameter file.

    Args:

	* fname       ->    Input parameter file.

    Returns:

	* rdict	      ->    Dictionary of parameters.'''

    rdict = collections.OrderedDict()
    infile = fopen(fname, ext='.par', mode='r')
    line = infile.readline()

    while line:
	llist = line.split()
	if len(llist):
	    if llist[0].endswith(":"):
		lkey = llist[0].rstrip(":")
		rdict[lkey] = []
		
		if len(llist)%2:
		    lenv = (len(llist)+1)//2
		else:
		    lenv = len(llist)

		for fval in (llist[1:lenv]):
		    try:
			rdict[lkey].append(ast.literal_eval(fval))
		    except:
			rdict[lkey].append(fval)

		if len(rdict[lkey]) == 1:
		    rdict[lkey] = rdict[lkey][0]

	line = infile.readline()

    infile.close()
    return rdict


#####Save list of variables to a HDF5 file
def saveh5(fname, ddict):
    '''Save a dictionary to a HDF5 file. Should be used for very small datasets only.
    
    Args:
    
        * fname         Name of the output file
        * ddict         Dictionary to be saved
        
    Returns:
        
        * None'''
    
    logging.info('Saving to File Name: %s'%(fname))

    fout = h5py.File(fname, 'w')   #No subgroups

    for each in list(ddict.keys()):
        sdat = fout.create_dataset(each, data=ddict[each])

    fout.close()

#####Load a dictionary of data from HDF5 file
def loadh5(fname):
    '''Load the contents of a HDF5 file into a dictionary. Should be used for very small datasets only.
    
    Args:
        
        * fname          Name of the HDF5 file
    
    Returns:
        * data           Dictionary with contents of HDF5 file
        
    .. warning:: 
        Do not use this with large arrays. Meant for small data.'''
    
    
    data = {}          #No subgroups

    fin = h5py.File(fname,'r')

    names = list(fin)
    for each in names:
        data[each] = fin[each].value

    return data

#############################End of File I/O utils############################

#############################Directory utils########################
def makedir(inlist):
    '''Creates directories listed in input list. Directories are not
    affected if they already exist.
    
    Args:
        
        * inlist    -> List of strings specifying the directories to be created
        
    Returns:
        
        * None'''
    
    for inp in inlist:
        if isinstance(inp, str)==False:
            raise ValueError('Directory names should be strings')
        
        if os.path.exists(inp) == False:
            os.mkdir(inp)

#########################End of directory utils####################


#########################Get screen width##########################
def screenWidth():
    try:
	import sys
	import fcntl
	import termios
	import struct

	lines, cols = struct.unpack('hh',  fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234'))
#		print('Terminal is %d lines high by %d chars wide' % (lines, cols))
    except:
	lines, cols = (100,80)

    return cols

###########################Simple progress bar######################
class ProgressBar:
    """ Creates a text-based progress bar. Call the object with 
    the simple `print'command to see the progress bar, which looks 
    something like this:

    [=======> 22% ]

    You may specify the progress bar's width, min and max values on init.
    
    .. note::
        Code originally from http://code.activestate.com/recipes/168639/"""

    def __init__(self, minValue = 0, maxValue = 100, totalWidth=None):
        self.progBar = "[]" # This holds the progress bar string
        self.min = minValue
        self.max = maxValue
	self.span = maxValue - minValue

	if totalWidth is None:
	    self.width = screenWidth()
	else:
	    self.width = totalWidth

        self.reset()

    def reset(self):
        '''Reset the counter to zero.'''
        self.start_time = time.time()
        self.amount = 0 # When amount == max, we are 100% done
        self.updateAmount(0) # Build progress bar string

    def updateAmount(self, newAmount = 0):
        """ Update the progress bar with the new amount (with min and max
        values set at initialization; if it is over or under, it takes the
        min or max value as a default. """
        if newAmount < self.min:
            newAmount = self.min
        if newAmount > self.max:
            newAmount = self.max
        self.amount = newAmount

        # Figure out the new percent done, round to an integer
        diffFromMin = np.float(self.amount - self.min)
        percentDone = (diffFromMin / np.float(self.span)) * 100.0
        percentDone = np.int(np.round(percentDone))

        # Figure out how many hash bars the percentage should be
        allFull = self.width - 2 - 18
        numHashes = (percentDone / 100.0) * allFull
        numHashes = np.int(np.round(numHashes))

        # Build a progress bar with an arrow of equal signs; special cases for
        # empty and full
        if numHashes == 0:
            self.progBar = '[>%s]' % (' '*(allFull-1))
        elif numHashes == allFull:
            self.progBar = '[%s]' % ('='*allFull)
        else:
            self.progBar = '[%s>%s]' % ('='*(numHashes-1),
                            ' '*(allFull-numHashes))
            # figure out where to put the percentage, roughly centered
            percentPlace = (len(self.progBar) / 2) - len(str(percentDone))
            percentString = ' ' + str(percentDone) + '% '
            elapsed_time = time.time() - self.start_time
            # slice the percentage into the bar
            self.progBar = ''.join([self.progBar[0:percentPlace], percentString,
                    self.progBar[percentPlace+len(percentString):], ])
            if percentDone > 0:
                self.progBar += ' %6ds / %6ds' % (int(elapsed_time),
                        int(elapsed_time*(100./percentDone-1)))

    def update(self, value, every=1):
        """ Updates the amount, and writes to stdout. Prints a
         carriage return first, so it will overwrite the current
          line in stdout."""
        if value % every == 0 or value >= self.max:
            self.updateAmount(newAmount=value)
            sys.stdout.write('\r' + self.progBar)
            sys.stdout.flush()

    def close(self):
        """Prints a blank space at the end to ensure proper printing
        of future statements."""
        print(' ')

################################End of progress bar class####################################


class LineCounter:
    '''Creates a text-base line counter.'''
    def __init__(self, txt, width=30):
        '''Setups the properties of the line counter.

        .. Args:

            * txt     -> Name of the counter
        
        .. Kwargs:

            * width   -> Width of the counter in chars.

        .. Returns:

            * None'''
        self.txt = txt
        self.count = 0
        print('\n')

    def update(self, newcount):
        '''Update the counter.'''
        self.count = newcount
        strg = '%s : %8d'%(self.txt,self.count)
        sys.stdout.write('\r' + strg)
        sys.stdout.flush()

    def increment(self):
        '''Increment the counter.'''
        self.count = self.count+1
        strg = '%s : %8d'%(self.txt,self.count)
        sys.stdout.write('\r' + strg)
        sys.stdout.flush()

    def close(self):
        print('\n')

############################################################
# Program is part of GIAnT v1.0                            #
# Copyright 2012, by the California Institute of Technology#
# Contact: earthdef@gps.caltech.edu                        #
############################################################
