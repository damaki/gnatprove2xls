#!/usr/bin/python3
#    gnatprove2xls.py - Exports GNATprove report files to spreadsheet format.
#    Copyright (C) 2017  Daniel King

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import xlwt
import re

# Regular expressions used to parse the GNATprove report file.
analysis_re   = re.compile(r'^Analyzed (\d+) units$')
unit_re       = re.compile(r'^in unit (.+), (\d+) subprograms and packages out of (\d+) analyzed$')
file_re       = re.compile(r'^  (.+) at (.+):(\d+)')
gen_file_re   = re.compile(r'^  (.+) at (.+):(\d+), instantiated at (.+):(\d+)')
flow_re       = re.compile(r'flow analyzed \((\d+) errors and (\d+) warnings\)')
proved_re     = re.compile(r'proved \((\d+) checks\)$')
not_proved_re = re.compile(r'not proved, (\d+) checks out of (\d+) proved$')
suppr_msg_re  = re.compile(r'^    (.+):(\d+):(\d+): (.+)$')


def parse_gnatprove_report(filename):
    """ Read a GNATprove report file and extract the detailed results for each unit.
    """
    
    results = {
        'numUnitsAnalyzed':None,
        'units':[]
    }
    
    file = open(filename, 'r')
    currentUnit = None
    
    try:
        for line in file:
            match = analysis_re.match(line)
            if match:
                results['numUnitsAnalyzed'] = int(match.group(1))
            
            match = unit_re.match(line)
            if match:
                # Save the contents of the previous compilation unit.
                if currentUnit:
                    results['units'].append(currentUnit)
                
                # Start a new compilation unit
                currentUnit = {
                    'name':match.group(1),
                    'numAnalyzed':int(match.group(2)),
                    'numTotal':int(match.group(3)),
                    'items':[]
                }
            
            file_match = file_re.match(line)
            gen_file_match = gen_file_re.match(line)
            if file_match or gen_file_match:
                
                if gen_file_match:
                    item = {
                        'name':gen_file_match.group(1),
                        'fileName':gen_file_match.group(2),
                        'lineNumber':gen_file_match.group(3),
                        'instFileName':gen_file_match.group(4),
                        'instLineNumber':gen_file_match.group(5),
                        'suppressions':[],
                        'numFlowErrors':0,
                        'numFlowWarnings':0,
                        'numChecks':0,
                        'numProvedChecks':0,
                        'flowAnalyzed':False,
                        'proved':False
                    }
                else:
                    item = {
                        'name':file_match.group(1),
                        'fileName':file_match.group(2),
                        'lineNumber':file_match.group(3),
                        'instFileName':None,
                        'instLineNumber':None,
                        'suppressions':[],
                        'numFlowErrors':0,
                        'numFlowWarnings':0,
                        'numChecks':0,
                        'numProvedChecks':0,
                        'flowAnalyzed':False,
                        'proved':False
                    }
                
                match = flow_re.search(line)
                if match:
                    item['flowAnalyzed'] = True
                    item['numFlowErrors'] = int(match.group(1))
                    item['numFlowWarnings'] = int(match.group(2))
                
                match = proved_re.search(line)
                if match:
                    item['proved'] = True
                    item['numChecks'] = int(match.group(1))
                    item['numProvedChecks'] = int(match.group(1))
                
                match = not_proved_re.search(line)
                if match:
                    item['proved'] = True
                    item['numChecks'] = int(match.group(2))
                    item['numProvedChecks'] = int(match.group(1))
                    
                currentUnit['items'].append(item)
                
            match = suppr_msg_re.match(line)
            if match:
                # Add the suppression to the last item read.
                currentUnit['items'][-1]['suppressions'].append({
                    'fileName':match.group(1),
                    'lineNumber':match.group(2),
                    'column':match.group(3),
                    'message':match.group(4).strip()
                })

        if currentUnit:
            results['units'].append(currentUnit)
    
    finally:
        file.close()
    
    return results
    
    
def to_percent(num, denom):
    if denom == 0:
        return 1
    else:
        return (num / denom)
        
        
def analysis_type(item):
    if item['flowAnalyzed']:
        if item['proved']:
            return 'flow + proof'
        else:
            return 'flow only'
    else:
        if item['proved']:
            return 'proof only'
        else:
            return 'not analyzed'
    

def count_unit_totals(unit):
    """Count the total number of errors/warnings/checks/suppressions in a unit
    """
    
    flowErrors = 0
    flowWarnings = 0
    checks = 0
    provedChecks = 0
    suppressions = 0

    for item in unit['items']:
        flowErrors   += item['numFlowErrors']
        flowWarnings += item['numFlowWarnings']
        checks       += item['numChecks']
        provedChecks += item['numProvedChecks']
        suppressions += len(item['suppressions'])
    
    return flowErrors, flowWarnings, checks, provedChecks, suppressions
    
def save_results(results, filename):
    """Save the parsed GNATprove report into a spreadsheet using the xlwt module
    """
    workbook = xlwt.Workbook()
    
    style_percent = xlwt.easyxf(num_format_str='0%')
    style_bold    = xlwt.easyxf(strg_to_parse='font: bold on')

    units_ws = workbook.add_sheet('Summary')
    units_ws.write(0, 0, 'Unit Name', style_bold)
    units_ws.write(0, 1, 'Analyzed', style_bold)
    units_ws.write(0, 2, 'Flow Errors', style_bold)
    units_ws.write(0, 3, 'Flow Warnings', style_bold)
    units_ws.write(0, 4, 'Checks', style_bold)
    units_ws.write(0, 5, 'Proved Checks', style_bold)
    units_ws.write(0, 6, '% Proved', style_bold)
    units_ws.write(0, 7, 'Suppressions', style_bold)
    
    row = 1
    for unit in results['units']:
        flowErrors, flowWarnings, checks, provedChecks, suppressions = count_unit_totals(unit)
        units_ws.write(row, 0, unit['name'])
        units_ws.write(row, 1, '{}/{}'.format(unit['numAnalyzed'], unit['numTotal']))
        units_ws.write(row, 2, flowErrors)
        units_ws.write(row, 3, flowWarnings)
        units_ws.write(row, 4, checks)
        units_ws.write(row, 5, provedChecks)
        if checks > 0:
            units_ws.write(row, 6, to_percent(provedChecks, checks), style_percent)
        units_ws.write(row, 7, suppressions)
        row += 1
        
    items_ws = workbook.add_sheet('Details')
    items_ws.write(0, 0, 'Name', style_bold)
    items_ws.write(0, 1, 'File', style_bold)
    items_ws.write(0, 2, 'Line', style_bold)
    items_ws.write(0, 3, 'Analysis', style_bold)
    items_ws.write(0, 4, 'Flow Warnings', style_bold)
    items_ws.write(0, 5, 'Flow Errors', style_bold)
    items_ws.write(0, 6, 'Checks', style_bold)
    items_ws.write(0, 7, 'Proved Checks', style_bold)
    items_ws.write(0, 8, '% Proved', style_bold)
    
    row = 1
    for unit in results['units']:
        for item in unit['items']:
            items_ws.write(row, 0, item['name'])
            items_ws.write(row, 1, item['fileName'])
            items_ws.write(row, 2, item['lineNumber'])
            items_ws.write(row, 3, analysis_type(item))
            
            if item['flowAnalyzed']:
                items_ws.write(row, 4, item['numFlowErrors'])
                items_ws.write(row, 5, item['numFlowWarnings'])
            if item['proved']:
                items_ws.write(row, 6, item['numChecks'])
                items_ws.write(row, 7, item['numProvedChecks'])
                if item['numChecks'] > 0:
                    items_ws.write(row, 8, to_percent(item['numProvedChecks'], item['numChecks']), style_percent)
            row += 1
            
    suppr_ws = workbook.add_sheet('Suppressed Messages')
    suppr_ws.write(0, 0, 'Name', style_bold)
    suppr_ws.write(0, 1, 'File', style_bold)
    suppr_ws.write(0, 2, 'Line', style_bold)
    suppr_ws.write(0, 3, 'Column', style_bold)
    suppr_ws.write(0, 4, 'Reason', style_bold)
    
    row = 1
    for unit in results['units']:
        for item in unit['items']:
            for suppr in item['suppressions']:
                suppr_ws.write(row, 0, item['name'])
                suppr_ws.write(row, 1, suppr['fileName'])
                suppr_ws.write(row, 2, suppr['lineNumber'])
                suppr_ws.write(row, 3, suppr['column'])
                suppr_ws.write(row, 4, suppr['message'])
                row += 1
    
    workbook.save(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export a GNATprove report file to spreadsheet format")
    parser.add_argument(
        'file', 
        nargs=1, 
        help="The GNATprove report file to parse"
    )
    parser.add_argument(
        '--out',
        nargs='?',
        help="Spreadsheet file to generate"
    )
    
    args = parser.parse_args()
    
    results = parse_gnatprove_report(args.file[0])
    
    if args.out:
        save_results(results, args.out)
