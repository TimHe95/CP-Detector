# -*- coding: UTF-8 -*-
import sys
import os
import commands
import time

# In some of the cpp/c files, add/remove some simple
# flags make the compilation successes.
#     e.g. -std=c++11
#     e.g. -fpermissive

# default configuration option
options = ['-O0', '-O1', '-O2', '-O3', '-Os', '-Ofast']
extensions = ['.cpp', '.cc', '.c', '.C', '.CC', '.CPP', '.Cpp']

# Global variables
class Glob:
	c_compiler = ''
	REPEATS = 1
	benchmark_dir = '' # Root directory of benchmark files.
	benchmarks = [] # Absolute path of each benchmark file.
   
   
def extract_time(output):
	
	compile_time_inMSMs = output.split('zbug_start')[1].split('zbug_end')[0].strip()
	
	m,s = compile_time_inMSMs.split(":")
	
	compile_time_in_sec = float(m)*60 + float(s)
	
	return compile_time_in_sec


def prepare_benchmarks(root):
    items = os.listdir(root)
    for item in items:
        path = os.path.join(root, item)
        if os.path.isdir(path):
            prepare_benchmarks(path)
        elif os.path.splitext('%s'%path)[1] in extensions:
            Glob.benchmarks.append(path)


def parse_args():

	# Error handling
	if not len(sys.argv) == 4:
		
		print('Argument Error. '
			'Usage:\n\tpython %s <c_compiler_name> <benchmark_dir> <repeats>'
			'\t\t<c_compiler_name> Only Support gcc, g++, clang or clang++'
			'\t\t<benchmark_dir>   The root directory of benchmark files.'
			'\t\t<repeats>         How many times do you want to run repeatedly for a case.'
			%(sys.argv[0]))
		exit(1)
		
	elif sys.argv[1] not in {'gcc', 'g++', 'clang', 'clang++'}:
		
		print('Argument 1 Error. Only gcc, g++, clang, clang++ is supported.')
		exit(1)

	elif not os.path.exists(sys.argv[2]) or os.path.isfile(sys.argv[2]):
		print('Argument 2 Error. Please give a valid directory.')
		exit(1)
	
	# write user parameters
	Glob.c_compiler = sys.argv[1]
	Glob.benchmark_dir = sys.argv[2]
	Glob.REPEATS = int(sys.argv[3])



def main():

	parse_args()
	prepare_benchmarks(Glob.benchmark_dir)

	# the error log. When compilation fails, write messages to it.
	logfile = open('log.err', 'w')

	# statistic
	suc = 0
	fail = 0
	total = len(options) * len(Glob.benchmarks)
	cur = 0

	# start performance testing.
	for j in range(0, len(Glob.benchmarks)):

		result_file = open('[Result]%s.txt'%Glob.benchmarks[j].split('/')[-1].split('.')[0], 'w')

		for i in range(0, len(options)):

			cur += 1
			
			compile_times = []
			cmd = '/usr/bin/time -f "zbug_start%%Ezbug_end" %s -std=c++11 %s %s -o %s.out'%(
				Glob.c_compiler, 
				options[i], 
				Glob.benchmarks[j], 
				Glob.benchmarks[j].split('/')[-1].split('.')[0]
				)
			
			(status, output) = commands.getstatusoutput(cmd)
			
			if status:
				
				fail += 1
				logfile.write('%s\n%s\n%s\n%s\n\n'%(40*'-', cmd, 40*'-', output))
				print('[%d/%d]Uncompilable: %s %s'%(
					cur,
					total,
					Glob.benchmarks[j].split('/')[-1], 
					options[i]
					))
			
			else:
				
				suc += 1
				compile_times.append(extract_time(output))
				
				for k in range(1, Glob.REPEATS):
					output = commands.getoutput(cmd)
					compile_times.append(extract_time(output))

				result_file.write('%s\t%s\n'%
					(
					options[i], 
					'\t'.join(str(aa) for aa in compile_times)
					))
				print('[%d/%d]OK, Finshed: %s %s'%(
					cur,
					total,
					Glob.benchmarks[j].split('/')[-1], 
					options[i]
					) )

		result_file.close()

	logfile.close()

	print('Final Result: OK %d/%d   NOT-OK %d/%d'%(
		suc, total, fail, total))

main()