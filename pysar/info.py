#!/usr/bin/env python3
############################################################
# Program is part of PySAR                                 #
# Copyright(c) 2013-2018, Zhang Yunjun, Heresh Fattahi     #
# Author:  Zhang Yunjun, Heresh Fattahi                    #
############################################################


import os
import argparse
import time
import h5py
from numpy import std
from pysar.utils import readfile, ptime
from pysar.objects import (geometry, 
                           giantIfgramStack, 
                           giantTimeseries, 
                           ifgramStack, 
                           timeseries, 
                           HDFEOS)


############################################################
EXAMPLE = """example:
  info.py timeseries.h5
  info.py velocity.h5
  info.py ifgramStack.h5

  # Time / Date Info
  info.py ifgramStack.h5 --date                             # print master/slave date pairs info of interferograms.
  info.py ifgramStack.h5 --date --nodrop > date12_list.txt  # save master/slave date pairs info of interferograms.
  info.py timeseries.h5  --date --num                       # print date list of timeseries with its number
  info.py LS-PARAMS.h5   --date > date_list.txt             # print date list of timeseries and save it to txt file.
  info.py S1_IW12_128_0593_0597_20141213_20180619.h5 --date

  # Slice / Dataset Info
  info.py timeseries.h5                              --slice
  info.py timeseries.h5                              --slice  --num
  info.py INPUTS/ifgramStack.h5                      --slice
  info.py S1_IW12_128_0593_0597_20141213_20180619.h5 --slice
  info.py LS-PARAMS.h5                               --slice
"""


def create_parser():
    """Create command line parser."""
    parser = argparse.ArgumentParser(description='Display Metadata / Structure information of ANY File',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=EXAMPLE)
    parser.add_argument('file', type=str, help='File to check')
    parser.add_argument('--compact', action='store_true',
                        help='show compact info by displaying only the top 20 metadata')
    parser.add_argument('--date', dest='disp_date', action='store_true',
                        help='Show date/date12 info of input file')
    parser.add_argument('--num', dest='disp_num', action='store_true',
                        help='Show date/date12 number')
    parser.add_argument('--nodrop', dest='drop_ifgram', action='store_true',
                        help='Do not display dropped interferograms info.')
    parser.add_argument('--slice', dest='disp_slice', action='store_true',
                        help='Print slice list of the file')
    return parser


def cmd_line_parse(iargs=None):
    """Command line parser."""
    parser = create_parser()
    inps = parser.parse_args(args=iargs)

    inps.max_meta_num = 200
    if inps.compact:
        inps.max_meta_num = 20
    return inps


############################################################
def attributes2string(atr, sorting=True, max_meta_num=200):
    ## Get Dictionary of Attributes
    digits = max([len(key) for key in list(atr.keys())] + [0])
    atr_string = ''
    i = 0
    for key, value in sorted(atr.items(), key=lambda x: x[0]):
        i += 1
        if i > max_meta_num:
            atr_string += '  ...\n'
            break
        else:
            # format metadata key/value
            try:
                value = value.decode('utf8')
            except:
                pass
            atr_string += '  {k:<{d}}    {v}\n'.format(k=key,
                                                       d=digits,
                                                       v=value)
    return atr_string


def print_attributes(atr, max_meta_num=200):
    atr_string = attributes2string(atr, max_meta_num=max_meta_num)
    print(atr_string)


def print_hdf5_structure(fname, max_meta_num=200):
    # generate string
    global h5_string, maxDigit
    h5_string = ''

    def hdf5_structure2string(name, obj):
        global h5_string, maxDigit
        if isinstance(obj, h5py.Group):
            h5_string += 'HDF5 group   "/{n}"\n'.format(n=name)
        elif isinstance(obj, h5py.Dataset):
            h5_string += ('HDF5 dataset "/{n:<{w}}": shape {s:<20}, '
                          'dtype <{t}>\n').format(n=name,
                                                  w=maxDigit,
                                                  s=str(obj.shape),
                                                  t=obj.dtype)
        atr = dict(obj.attrs)
        if len(atr) > 0:
            h5_string += attributes2string(atr, max_meta_num=max_meta_num)+"\n"

    f = h5py.File(fname, 'r')
    # grab metadata in root level as it will be missed in hdf5_structure2string()
    atr = dict(f.attrs)
    if len(atr) > 0:
        h5_string += 'Attributes in / level:\n'
        h5_string += attributes2string(atr, max_meta_num=max_meta_num)+'\n'

    # get maxDigit value 
    maxDigit = max([len(i) for i in f.keys()])
    maxDigit = max(20, maxDigit+1)
    if atr.get('FILE_TYPE', 'timeseries') == 'HDFEOS':
        maxDigit += 35

    # get structure string
    f.visititems(hdf5_structure2string)
    f.close()

    # print string
    print(h5_string)
    return h5_string


############################################################
def print_timseries_date_stat(dateList):
    datevector = ptime.date_list2vector(dateList)[1]
    print('Start Date: '+dateList[0])
    print('End   Date: '+dateList[-1])
    print('Number of acquisitions    : %d' % len(dateList))
    print('Std. of acquisition times : %.2f yeras' % std(datevector))
    print('----------------------')
    print('List of dates:')
    print(dateList)
    print('----------------------')
    print('List of dates in years')
    print(datevector)
    return


def print_date_list(fname, disp_num=False, drop_ifgram=False, print_msg=False):
    """Print time/date info of file"""
    atr = readfile.read_attribute(fname)
    k = atr['FILE_TYPE']
    dateList = None
    if k in ['timeseries']:
        dateList = timeseries(fname).get_date_list()
    elif k == 'HDFEOS':
        obj = HDFEOS(fname)
        obj.open(print_msg=False)
        dateList = obj.dateList
    elif k == 'giantTimeseries':
        obj = giantTimeseries(fname)
        obj.open(print_msg=False)
        dateList = obj.dateList
    elif k in ['ifgramStack']:
        dateList = ifgramStack(fname).get_date12_list(dropIfgram=drop_ifgram)
    elif k in ['giantIfgramStack']:
        obj = giantIfgramStack(fname)
        obj.open(print_msg=False)
        dateList = obj.date12List
    else:
        print('--date option can not be applied to {} file, ignore it.'.format(k))

    if print_msg and dateList is not None:
        for i in range(len(dateList)):
            if disp_num:
                print('{}\t{}'.format(dateList[i], i))
            else:
                print(dateList[i])
    return dateList


def print_slice_list(fname, disp_num=False, print_msg=False):
    """Print slice info of file"""
    slice_list = readfile.get_slice_list(fname)
    if print_msg:
        for i in range(len(slice_list)):
            if disp_num:
                print('{}\t{}'.format(slice_list[i], i))
            else:
                print(slice_list[i])
    return slice_list


def print_pysar_info(fname):
    try:
        atr = readfile.read_attribute(fname)
        k = atr['FILE_TYPE']
        print('{} {:*<40}'.format('*'*20, 'Basic File Info '))
        print('file name: '+atr['FILE_PATH'])
        print('file type: '+atr['FILE_TYPE'])
        if 'Y_FIRST' in atr.keys():
            print('coordinates : GEO')
        else:
            print('coordinates : RADAR')
        if k in ['timeseries']:
            dateList = print_date_list(fname)
            print('\n{} {:*<40}'.format('*'*20, 'Date Stat Info '))
            print_timseries_date_stat(dateList)
    except:
        pass
    return


############################################################
def main(iargs=None):
    inps = cmd_line_parse(iargs)
    if not os.path.isfile(inps.file):
        print('ERROR: input file does not exists: {}'.format(inps.file))
        return
    ext = os.path.splitext(inps.file)[1].lower()

    # --date option
    if inps.disp_date:
        print_date_list(inps.file, disp_num=inps.disp_num, drop_ifgram=inps.drop_ifgram, print_msg=True)
        return

    # --slice option
    if inps.disp_slice:
        print_slice_list(inps.file, disp_num=inps.disp_num, print_msg=True)
        return

    # Basic info from PySAR reader
    print_pysar_info(inps.file)

    # Generic Attribute/Structure of all files
    if ext in ['.h5', '.he5']:
        print('\n{} {:*<40}'.format('*'*20, 'HDF5 File Structure '))
        print_hdf5_structure(inps.file, max_meta_num=inps.max_meta_num)
    else:
        print('\n{} {:*<40}'.format('*'*20, 'Binary File Attributes '))
        atr = readfile.read_attribute(inps.file)
        print_attributes(atr, max_meta_num=inps.max_meta_num)

    return


############################################################
if __name__ == '__main__':
    main()
