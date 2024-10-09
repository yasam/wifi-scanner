#!/usr/bin/python3

import argparse
import subprocess
import sys
import mimetypes
import timeit
import json
from io import StringIO
import csv
from mac_vendor_lookup import MacLookup
import copy


def debug(str):
    global verbose
    if verbose:
        print(str)

def runcommand(cmd):
    global verbose
    result = None
    cmd_l = cmd.split()
    
    debug("---Executing :" + cmd)
    
    try:
        result = subprocess.run(cmd_l, check=True, capture_output=True)
    except subprocess.CalledProcessError as err:
        print(err)

    debug("---result:")
    debug(result.stdout.decode())
    return result

def scan():
    result = runcommand("netsh wlan show networks mode=bssid")
    #result = runcommand("netsh wlan show all")
    return result.stdout.decode()

def get_networks(str):
    lines  = str.splitlines()
    l = len(lines)
    start = 0
    end = 0
    for i in range(l):
        print(lines[i])
        if start == 0 and "SHOW NETWORKS MODE=BSSID" in lines[i]:
            start = i + 6 
        if end == 0 and "SHOW INTERFACE CAPABILITIES" in lines[i]:
            end = i - 3
            break
    
    list(map(debug, lines[start:end]))

    return lines[start:end]

def parse_result(str):
    #all = get_networks(str)
    all = str.splitlines()
    #list(map(debug, all))
    #print(*all, sep = "\n")
    ssids = []
    idx = 1
    found = False
    ssids = []
    ssid = {}
    for l in all:
        if l.strip() == "":
            continue
        ssid_str = 'SSID %d :' % idx
        if ssid_str in l:
            idx = idx + 1
            name = l.split(':')[1].strip()
            #print(name)
            if found:
                ssids.append(ssid)
                ssid = {}
            ssid['ssid'] = name
            ssid['content'] = []
            found = True
        else:
            if found == False:
                continue
            ssid['content'].append(l)
    return ssids

def get_manufacturer(mac):
    try:
        return MacLookup().lookup(mac)
    except:
        x = int(mac[0:2], 16) & 2
        if x == 0:
            return ""
        return "-----Locally admnistered"

def parse_ssid_content(content):
    ssid = {}
    idx = 1
    found = False
    ssid['bssids'] = []
    bssid = None
    for e in content:
        #parse key value first
        attr = e.split(':')
        name = attr[0].strip()
        value = '-'.join(attr[1:]).strip()
        # if it is Channel, convert value to integer
        if name == 'Channel':
            value = int(value)

        # generate search string for BSSID
        ap = 'BSSID %d' % idx
        if ap in e:
            # Found new BSSID
            idx = idx + 1
            found = True
            # append the previous bssid
            if bssid != None:
                ssid['bssids'].append(bssid)
            # create new bssid object
            bssid = {}
            bssid['MAC'] = value
            bssid['Manufacturer'] = get_manufacturer(bssid['MAC'])
            #print(value)
        else:
            if found == False :
                # fill SSID values
                ssid[name] = value
            else:
                # fill BSSID values
                bssid[name] = value
    
    ssid['bssids'].append(bssid)

    return ssid

def make_bssid_list(ssids):
    #serialize all bssid information in a single object
    slist = []
    for s in ssids:
        t = copy.deepcopy(s)
        del t['bssids']
        for bssid in s['bssids']:
            e = copy.deepcopy(bssid)
            e.update(t)
            slist.append(e)
    
    return slist

def print_bssids(slist):
    print('--- ------------------------------ ------------------ ------- ------ ---------- -------------------- ---------- --------------------')
    print('%-3s %-30s %-18s %-7s %-6s %-10s %-20s %-10s %-20s' % ('No', 'SSID', 'MAC', 'Channel', 'Signal', 'Radio type', 'Auth', 'Encr', 'Manufacturer'))
    print('--- ------------------------------ ------------------ ------- ------ ---------- -------------------- ---------- --------------------')

    '''
    Black: \u001b[30m
    Red: \u001b[31m
    Green: \u001b[32m
    Yellow: \u001b[33m
    Blue: \u001b[34m
    Magenta: \u001b[35m
    Cyan: \u001b[36m
    White: \u001b[37m
    Reset: \u001b[0m
    '''
    color=[u"\u001b[31m", u"\u001b[34m"]
    idx = 1  
    for s in slist:
        #print('%3d %s %-30s %-18s %-7d %-6s %-10s %-20s %-10s %-20s %s' % (color[idx%2], idx, s['ssid'], s['mac'], s['Channel'], s['Signal'], s['Radio type'], s['Authentication'], s['Encryption'], s['manufacturer'], u"\u001b[0m"))
        print('%3d %-30s %-18s %-7d %-6s %-10s %-20s %-10s %-20s' % ( idx, s['ssid'], s['MAC'], s['Channel'], s['Signal'], s['Radio type'], s['Authentication'], s['Encryption'], s['Manufacturer']))
        #print(s)
        idx = idx + 1

def print_result(str, ssid, channel):
    for line in str.splitlines():
        print(line)

def main():
    global verbose
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-s", "--sortby", help="Sort by any field such as SSID, MAC, Channel, Signal, etc.", default="ssid")
    argparser.add_argument('-v', '--verbose', action='store_true')

    args = argparser.parse_args()

    verbose = args.verbose
    #verbose = True

    s = scan()
    ssids_raw = parse_result(s)
    ssids = []
    for raw in ssids_raw:
        #print(raw['name'])
        ssid = parse_ssid_content(raw['content'])
        ssid['ssid'] = raw['ssid']
        ssids.append(ssid)

    slist = make_bssid_list(ssids)
    slist.sort(key=lambda k: (k[args.sortby], k['MAC']))
    print_bssids(slist)
	
if __name__ == "__main__":
	main()



