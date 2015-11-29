#!/usr/bin/python3

import os
import json
import subprocess
import matplotlib
import optparse

matplotlib.use('svg')  # must come before pyplot import

import matplotlib.pyplot as plt

optparser = optparse.OptionParser()

optparser.add_option('-d', '--mountpoint', dest='mountpoint', default='.',
                     help='Test disk mounted at MOUNTPOINT', metavar='MOUNTPOINT')
optparser.add_option('-s', '--filesize', dest='filesize', default='100G',
                     help='Set SIZE as file size for test', metavar='SIZE')
optparser.add_option('-m', '--max-concurrency', dest='maxdepth', default=128, type='int',
                     help='Test maximum concurrency level N', metavar='N')

(options, args) = optparser.parse_args()

mountpoint = options.mountpoint
filesize = options.filesize
maxdepth = options.maxdepth

header = '''\
[global]
ioengine=libaio
buffered=0
rw=randread
bs=4k
size={filesize}
directory={mountpoint}
runtime=10s
filename=fiotest.tmp
group_reporting=1

'''

job_template = '''\
[{jobname}]
iodepth={depth}
{new_group}

'''

max_threads = os.cpu_count()

def create_fio_spec(fname):
    with open(fname, 'w') as f:
        f.write(header.format(**globals()))
        last = 0
        growth = 1.1
        for depth in range(1, maxdepth):
            if depth < last * growth:
                continue
            depth_remain = depth
            threads_remain = max_threads
            new_group = 'stonewall'
            # distribute load among max_threads
            while depth_remain:
                depth_now = int(depth_remain / threads_remain)
                if depth_now:
                    f.write(job_template.format(jobname=depth, depth=depth_now, new_group=new_group))
                    new_group = ''
                    depth_remain -= depth_now
                threads_remain -= 1
            last = depth

def run_job():
    spec_fname = 'tmp.fio'
    create_fio_spec(spec_fname)
    result_json = subprocess.check_output(['fio', '--output-format=json', spec_fname])
    result_json = result_json.decode('utf-8')
    open('tmp.fio.json', 'w').write(result_json)
    return json.loads(result_json)


results = run_job()

concurrencies = [0]  # FIXME: fake 0 element to force axis limit
latencies = [0.]
iopses = [0.]

for job in results['jobs']:
    concurrency = int(job['jobname'])
    latency = float(job['read']['clat']['mean'])
    latency_stddev = float(job['read']['clat']['stddev'])
    iops = float(job['read']['iops'])
    concurrencies.append(concurrency)
    latencies.append(latency)
    iopses.append(iops)

def fix_y_axis(plt):
    plt.ylim(0.0, plt.ylim()[1])

fig, ax1 = plt.subplots()
ax1.plot(concurrencies, iopses, 'b-')
ax1.set_xlabel('concurrency')
# Make the y-axis label and tick labels match the line color.
ax1.set_ylabel('4k read iops', color='b')
for tl in ax1.get_yticklabels():
    tl.set_color('b')
# FIXME: want log scale on X axis
    
ax2 = ax1.twinx()
ax2.plot(concurrencies, latencies, 'r-')
ax2.set_ylabel('average latency (μs)', color='r')
for tl in ax2.get_yticklabels():
    tl.set_color('r')
    
plt.savefig(filename='disk-concurrency-response.svg')