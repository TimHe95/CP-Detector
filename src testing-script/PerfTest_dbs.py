import pexpect
import os
import commands
import time
import sys
import signal

# set to True for newer version of mysql
v2 = False
v3 = True


mariadb_user = 'root'
mariadb_socket = '/var/lib/mysql/mysql.sock'
# install sysbench first, lua will be here.
sysbench_lua_prefix = '/usr/share/sysbench/lua/'
mariadb_prefix = '/usr/local/mysql/'
mariadb_sample_result = '../7_oltp_write_only(INNODB_FLUSH_METHOD)' # sample result file
output_dir = '../bin/[RES]innodb_flush_method(8.0)'
# This directory will include : 
#	(1) checkpoint file when job not finished and Ctr+C recived.
#	(2) raw test output printed by sysbench format: "[suc]/[fail]_ID.txt"

wkld_separator = '--innodb' # prefix for the first configuration-parameter in the sample result file (no matter parameters after this)
test_time = 10 # time to test as expected, but may not as desired.
wait_time = 15 # time in seconds to wait until the test is over, if unfinished, force it.
parameter_stop_words = ['nil', '-1']

SLEEP_INTERVAL = 500 # let system rest for a while each this much samples
SLEEP_TIME = 10 # seconds each rest last for

RESET_INTERVAL = 100 # let mysql reset all data in /usr/local/bin/mysql/data for limited disk space

##### These are stop/init/ping MySQL Server
shutdown_cmd = '%sbin/mysqladmin shutdown -S%s'%(mariadb_prefix, mariadb_socket)
ping_cmd = '%sbin/mysqladmin ping -S%s'%(mariadb_prefix, mariadb_socket)
create_db_cmd = '%sbin/mysqladmin create sbtest -S%s'%(mariadb_prefix, mariadb_socket)
drop_db_cmd = '%sbin/mysqladmin drop sbtest -S%s'%(mariadb_prefix, mariadb_socket)

##### These commands are made for reinstall db
clean_mysql_dir_cmd = 'rm -rf %sdata/*'%mariadb_prefix
clean_mysql_dir_cmd_v2 = 'rm -rf %sdata'%mariadb_prefix
reset_prep_cmd1 = 'mkdir %sdata/mysql'%mariadb_prefix
reset_prep_cmd1_v2 = ''
reset_prep_cmd2 = 'mkdir %sdata/test'%mariadb_prefix
reset_prep_cmd2_v2 = ''
reset_cmd = '%sscripts/mysql_install_db --user=mysql'%mariadb_prefix
reset_cmd_v2 = '%sbin/mysql_install_db --user=mysql --basedir=/usr/local/mysql/ --datadir=/usr/local/mysql/data'%mariadb_prefix
reset_cmd_v3 = '%sbin/mysqld --initialize --user=mysql --basedir=/usr/local/mysql/ --datadir=/usr/local/mysql/data'%mariadb_prefix # for MySQL 8.x
if v2:
	clean_mysql_dir_cmd = clean_mysql_dir_cmd_v2
	reset_prep_cmd1 = reset_prep_cmd1_v2
	reset_prep_cmd2 = reset_prep_cmd2_v2
	reset_cmd = reset_cmd_v2
if v3:
        clean_mysql_dir_cmd = clean_mysql_dir_cmd_v2
        reset_prep_cmd1 = reset_prep_cmd1_v2
        reset_prep_cmd2 = reset_prep_cmd2_v2
        reset_cmd = reset_cmd_v3
#reset_cmd2 = 'chown -R root %s'%mariadb_prefix
#reset_cmd3 = 'chown -R mysql %sdata'%mariadb_prefix

def perform_drop_db():
	child = pexpect.spawn(drop_db_cmd)
	child.timeout = 10
	index = child.expect_exact([pexpect.TIMEOUT, '[y/N]'])
	if index == 0:
		child.kill(0)
	elif index == 1:
		child.sendline('y')
		child.wait() # child.interact() or child.read()
		print ('[%s] DB: \'sbtest\' dropped.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	return

def have_a_rest():
	print ('[%s] ~ Leisure time! ~ '%(time.strftime("%Y-%m-%d %H:%M:%S")))
	sentence = "HaveARest"
	for char in sentence.split():
	   allChar = []
	   for y in range(12, -12, -1):
	       lst = []
	       lst_con = ''
	       for x in range(-30, 30):
	            formula = ((x*0.05)**2+(y*0.1)**2-1)**3-(x*0.05)**2*(y*0.1)**3
	            if formula <= 0:
	                lst_con += char[(x) % len(char)]
	            else:
	                lst_con += ' '
	       lst.append(lst_con)
	       allChar += lst
	   print('\n'.join(allChar))
	time.sleep(SLEEP_TIME)


# ----------------------------- recovering -----------------------------
def do_recover():

	check_point_offset = []
	sample_offset = 0
	suc_offset = 0
	fail_offset = 0

	if os.path.exists('%s/checkpoint'%output_dir) :
		print ('[%s] Recovering from checkpoint...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
		ck_f = open('%s/checkpoint'%output_dir, 'r')
		check_point_offset = ck_f.readline().strip().split(' ')
		ck_f.close()
		try:
			sample_offset = int(check_point_offset[0])
			suc_offset = int(check_point_offset[1])
			fail_offset = int(check_point_offset[2])
			os.remove('%s/checkpoint'%output_dir)
		except Exception as e:
			sample_offset = 0
			suc_offset = 0
			fail_offset = 0
			print ('[Warning] checkpoint file read error. Start from begining.')
	else :
		print ('[%s] No checkpoint, starting from begining.'%(time.strftime("%Y-%m-%d %H:%M:%S")))

	return sample_offset, suc_offset, fail_offset
# -----------------------------------------------------------------------
sample_offset, suc_offset, fail_offset = do_recover()


# ------------------------------- parameters extracting -------------------------------
mariadb_file = open(mariadb_sample_result, 'r')
mariadb_lines = mariadb_file.readlines()
mariadb_file.close()

mariadb_head = mariadb_lines[0].strip().split('\t')
mariadb_body = mariadb_lines[1:]
table_size_index = mariadb_head.index('--table-size') # for sorting samples

def get_separator_loc(head):
	separate_loc = 0
	for param in head:
		if wkld_separator in param:
			break
		separate_loc += 1
	if separate_loc == 0:
		print ('wkld_separator error. Exit.')
		exit(0)
	return separate_loc

separate_loc = get_separator_loc(mariadb_head)

wkld_head = mariadb_head[0:separate_loc]
conf_head = mariadb_head[separate_loc:]
# --------------------------------------------------------------------------------------
sample_count = 0 + sample_offset
sample_total = len(mariadb_body)
successed = 0 + suc_offset
failed = 0 + fail_offset



# ------------------------------ signal handling ------------------------------
def onsignal_term(signum, frame):
	global sample_count
	#global sample_offset
	#global successed
	#global failed
	if sample_count == sample_offset:
		sample_count += 1
	print ('[%s] SIGTERM received (>kill), saving...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	ck = open('%s/checkpoint'%output_dir, 'w')
	ck.write('%d %d %d'%(sample_count-1, successed, failed))
	ck.close()
	print ('[%s] DONE.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	exit(0)

def onsignal_int(signum, frame):
	global sample_count # if no write on this variable, 'global' should be removed
	if sample_count == sample_offset:
		sample_count += 1
	print ('[%s] SIGINT received (Ctrl+C), saving...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	ck = open('%s/checkpoint'%output_dir, 'w')
	ck.write('%d %d %d'%(sample_count-1, successed, failed))
	ck.close()
	print ('[%s] DONE.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	exit(0)


signal.signal(signal.SIGTERM, onsignal_term)
signal.signal(signal.SIGINT, onsignal_int)
# -----------------------------------------------------------------------------

def reset_mysql():

	# print ('[%s] Cleaning .../mysql/data dir.'%(time.strftime("%Y-%m-%d %H:%M:%S"))
	# rm -rf mysql/data/*  |  rm -rf mysql/data
        err = commands.getstatusoutput(clean_mysql_dir_cmd)
	if err[0]==0 :
		print ('[%s] Cleaning Done. Reseting.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	else:
		print ('[%s] Cleaning failed because \'rm data\' failed. Stop.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
		exit(1)

	commands.getstatusoutput(reset_prep_cmd1) # mkdir mysql/data/test
	commands.getstatusoutput(reset_prep_cmd2) # mkdir mysql/data/mysql

	pwd = os.getcwd() # save current working dir
	os.chdir(mariadb_prefix)
	prep_res = commands.getstatusoutput(reset_cmd) # install db
	if 'OK' in prep_res[1]:
		print ('\tInstalling Mariadb/MySQL/PostgreSQL system tables in \'mysql/data\', OK')
	else :
		print ('\tInstalling Mariadb/MySQL/PostgreSQL system tables FAILED!')
		exit(1)
	os.chdir(pwd)

	print ('[%s] Reseting Done.'%(time.strftime("%Y-%m-%d %H:%M:%S")))

def gen_sysbench_cmd(wkld_params):

	# for connection parameters
	sysbench_cmd = 'sysbench %s%s'%(sysbench_lua_prefix, wkld_params[0])
	sysbench_cmd = '%s --mysql-socket=%s --mysql-user=%s'%(sysbench_cmd, mariadb_socket, mariadb_user)

	# for workload parameters
	for i in range(1, len(wkld_params)): # wkld_params[0] is 'sysbench'
		if wkld_params[i] in parameter_stop_words:
			continue
		sysbench_cmd = '%s %s=%s' % (sysbench_cmd, wkld_head[i] , wkld_params[i])
	sysbench_cmd = sysbench_cmd + ' --mysql-ignore-errors=all --time=%d  --forced-shutdown=%d'%(test_time, wait_time)

	sysbench_prepare = sysbench_cmd + ' prepare'
	sysbench_warmup = sysbench_cmd + ' warmup'
	sysbench_run = sysbench_cmd + ' run'

	return sysbench_prepare, sysbench_warmup, sysbench_run


def gen_mysqld_cmd(conf_params):

	mysqld_cmd = '%sbin/mysqld_safe '%mariadb_prefix

	for j in range(0, len(conf_params)):
		if conf_params[j] in parameter_stop_words:
			continue
		mysqld_cmd = '%s %s=%s' % (mysqld_cmd, conf_head[j], conf_params[j])

	mysqld_cmd = mysqld_cmd + ' &' # run background

	return mysqld_cmd


def do_start_mysqld(mysqld_cmd):

	ttl = 80
	next_sample = False
	
	print(mysqld_cmd)
	os.system(mysqld_cmd) # start mysqld

	while (commands.getstatusoutput(ping_cmd)[0]): # continously ping until success or time out
		time.sleep(0.1)
		ttl -= 1
		if ttl == 0:
			next_sample = True
			break
	
	if next_sample == True: # time out handling
		os.system(mysqld_cmd) # give it one last chance, start mysqld again
		time.sleep(2)
		if not commands.getstatusoutput(ping_cmd)[0]:# great! it grab the chance.
			print ('[%s] mysqld started!(by last chance)'%(time.strftime("%Y-%m-%d %H:%M:%S")))
			return True
		print ('[%s] mysqld start timeout, next sample.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
		return False

	print ('[%s] mysqld started!'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	return True


def do_shutdown_mysqld(shutdown_cmd):

	ttl = 100
	next_sample = False

        print(shutdown_cmd)
        os.system(shutdown_cmd) # shutdown mysqld

        while (not commands.getstatusoutput(ping_cmd)[0]): # continously ping until success or time out
                time.sleep(0.1)
                ttl -= 1
                if ttl == 0:
                        next_sample = True
                        break

        if next_sample == True: # time out handling
                print ('[%s] mysqld shutdown timeout, next sample.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
                return False

        print ('[%s] mysqld shutdown success!'%(time.strftime("%Y-%m-%d %H:%M:%S")))
        return True

def do_garbage_cleaning():

	if (commands.getstatusoutput(create_db_cmd)[0]):
		print ('[%s] DB: \'sbtest\' exists, drop and recreate it.'%(time.strftime("%Y-%m-%d %H:%M:%S")))

		perform_drop_db()

		if (0 == commands.getstatusoutput(create_db_cmd)[0]): # maybe no else here.
			print ('\trecreate OK.')
	else :
		print ('[%s] DB: \'sbtest\' created.'%(time.strftime("%Y-%m-%d %H:%M:%S")))


def do_preparing_data(sysbench_prepare, sample_count):

	print ('[%s] preparing data...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	prep_res = commands.getstatusoutput(sysbench_prepare)

	if prep_res[0] == 0 :
		print ('\t--OK.')
		return True
	else:
		errlog = open('%s/err_prep_%s.txt'%(output_dir, sample_count), 'w')
		errlog.write(prep_res[1])
		errlog.close()

		print ('\t --not OK, see %s/err_prep%s.txt for more INFO.'%(output_dir, sample_count))
		print ('[%s] Doing cleanning up.'%(time.strftime("%Y-%m-%d %H:%M:%S")))

		perform_drop_db()

		print ('[%s] One finished, shutting down mysqld.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
		commands.getstatusoutput(shutdown_cmd)

		return False

def do_running(sysbench_run, sample_count):

	print ('[%s] running...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	run_res = commands.getstatusoutput(sysbench_run)
	if run_res[0] == 0 :
		print ('\t--OK :)')
		successed = True
		file_name = '%s/out_suc_%s.txt'%(output_dir, sample_count)
	else :
		print ('\t--not OK :(')
		successed = False
		file_name = '%s/out_fail_%s.txt'%(output_dir, sample_count)
	res_file = open(file_name, 'w')
	res_file.write(run_res[1])
	res_file.close()

	return successed

def get_stat(prev, cur):
	if cur == prev:
		return False
	else:
		return True

prev_table_size = -1

for mariadb_line in mariadb_body[sample_offset:]: # for each test case

	sample_count += 1

	if sample_count % SLEEP_INTERVAL == 0 :
		have_a_rest()

	if sample_count % RESET_INTERVAL == 0 :
		reset_mysql()
		prev_table_size = -1

	mariadb_params = mariadb_line.strip().split('\t')

	# ---------------- for sysbench cmdline ----------------
	wkld_params = mariadb_params[0:separate_loc]
	sysbench_prepare, sysbench_warmup, sysbench_run = gen_sysbench_cmd(wkld_params)

	# ---------------- for mysqld cmdline ----------------
	conf_params = mariadb_params[separate_loc:]
	mysqld_cmd = gen_mysqld_cmd(conf_params)

	# ---------------- decide whether to reprepare data ----------------
	prep_data = get_stat(prev_table_size, wkld_params[table_size_index])
	prev_table_size = wkld_params[table_size_index]


# --------------------------- run this sample ----------------------------
	print ('************** Case [%d/%d] successed/failed:[%d:%d] **************'%(sample_count, sample_total, successed, failed))

	print ('[%s] Make sure mysqld to shutdown.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	commands.getstatusoutput(shutdown_cmd)
	time.sleep(3)
	#if not do_shutdown_mysqld(shutdown_cmd):
	#	failed += 1
        #        continue

    # ------------------------ mysqld starting step ------------------------
	if not do_start_mysqld(mysqld_cmd):
		failed += 1
		continue

	# ------------------------ garbage cleaning step ------------------------
	if prep_data:
		do_garbage_cleaning()
		# --------------------- preparing data step ---------------------
		if not do_preparing_data(sysbench_prepare, sample_count):
			failed += 1
			prev_table_size = -1
			continue

    # ------------------------ warming up data step ------------------------
	print ('[%s] warming up data...'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	commands.getstatusoutput(sysbench_warmup)

	# ------------------------ runing step ------------------------
	if do_running(sysbench_run, sample_count):
		successed += 1
	else:
		failed += 1

	# ------------------------ cleaning up step ------------------------
	if sample_count == sample_total:
		print ('[%s] All sample done. Doing cleanning up.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
		perform_drop_db()
	else:
		print ('[%s] NO cleanning up.'%(time.strftime("%Y-%m-%d %H:%M:%S")))

	# ------------------------ mysqld shutdown step ------------------------
	print ('[%s] One finished, shutting down mysqld.'%(time.strftime("%Y-%m-%d %H:%M:%S")))
	commands.getstatusoutput(shutdown_cmd)
