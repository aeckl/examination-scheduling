#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
PATHS = os.getcwd().split('/')
PROJECT_PATH = ''
for p in PATHS:
    PROJECT_PATH += '%s/' % p
    if p == 'examination-scheduling':
        break
sys.path.append(PROJECT_PATH)

import csv
from model.instance import build_smart_random
from visualization.comparator import compute_performance
from visualization.results_provider import convert_performance_file_to_table
from visualization.graphicer import generate_file
from argparse import ArgumentParser
from inputData import examination_data


def provide_results(input_file, data_type='smart', **kwards):
    """ @param input_file: a template taht represents what we want. csv file
        on the lines we have the problems, on the columns the data, for wich we want a result
    """
    # collect data and problem we want
    datas, probs = [], []
    with open('%svisualization/data/%s.csv' % (PROJECT_PATH, input_file)) as src:
        reader = csv.reader(src, delimiter='\t')
        row = reader.next()
        datas = [col for col in row[2:] if col]
        row = reader.next()
        while row:
            if row[0]:
                probs.append(row[0])
            try:
                row = reader.next()
            except StopIteration:
                break

    # compute for each problem and each kind of data the performance
    for prob in probs:
        if data_type == 'real':
            input_data = examination_data.read_data(semester="15W")
            x, y = compute_performance(prob, input_data, **kwards)
            generate_file(x, y, input_data, name=prob, with_room_label=False)
        else:
            for data in datas:
                dimensions = {d.split('=')[0].lower(): int(d.split('=')[1]) for d in data.split(', ')}
                if data_type == 'smart':
                    input_data = build_smart_random(n=dimensions['n'], r=dimensions['r'], p=dimensions['p'])
                elif data_type == 'real':
                    input_data = examination_data.read_data(semester="15W")
                x, y = compute_performance(prob, input_data, **kwards)

                generate_file(x, y, input_data, name=prob, with_room_label=False)

    # collect the data in tab and write it on a file
    convert_performance_file_to_table(last_nb=len(probs) * len(datas))


def main():
    p = ArgumentParser()
    p.add_argument('-f', '--file', required=True, help='<Required> give the template file you want to fill in')
    p.add_argument('-t', '--type', default='smart', help='<Default: smart> wich data do we use?')
    args = p.parse_args()

    provide_results(args.file, data_type=args.type)


if __name__ == '__main__':
    main()
