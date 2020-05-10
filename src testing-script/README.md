## GCC Clang test script

### Step 1

copy benchmark file to `/dir/to/benchmarks`

### Step 2

run

```
python PerfTest_c-compiler.py <c/c++_compiler_name> </dir/to/benchmarks> <repeats>
```

* `<c/c++ compiler name>` gcc g++ clang clang++
* `</dir/to/benchmarks>` benchmark dir
* `<repeats>` [1,∞) times of repeations (20 in paper) 

### Step 3

result will be shown in current dir, beginning with `[Result]`.  
log.err shows the source file that can not compile

# MySQL/MariaDB/PostgreSQL

> Default for version 5.1/5.6/5.7. If testing 8.x, changing the variable `reset_cmd_v3` in source to `/usr/local/mysqld --initialize`

### Change these variables to suit your env：

* `mariadb_socket` is `/tmp/mysql.sock` or not
* `sysbench_lua_prefix` lua testing script dir
* `output_dir` result will be shown here
* `mariadb_sample_result` the output of `pict`, which specify the combinations of target option, scenarios and configuration options.

For `mariadb_sample_result`, we use `pict` to generate combinations of target option, scenarios and configuration options. For instance, if target option is `innodb_buffer_pool_size`, then it may be:
```
sysbench	--table-size	--tables	--threads	--mysql-storage-engine	--innodb-buffer-pool-size	--innodb-log-file-size
"oltp_write_only.lua"	60000	10	25	innodb	1M	200M	2000
"oltp_write_only.lua"	80000	10	25	innodb	16M	200M	2000
"oltp_write_only.lua"	40000	10	25	innodb	256M	200M	2000
"oltp_write_only.lua"	100000	10	1	innodb	1M	200M	2000
"oltp_write_only.lua"	60000	10	100	innodb	8M	200M	2000
.... .... .... ....
```

### How to use `pict` to get above file

[pict](https://github.com/microsoft/pict)

This should be the very initial input file `conf_variable_and_values.txt`：
```
###########################
###    Basic Scripts    ###
###########################

sysbench: "oltp_read_write.lua"

###########################
### workload  variables ###
###########################

# Number of rows per table(10000)
--table-size: 10, 40000, 100000, 200000, 400000, 600000, 800000, 1000000

--tables: 10

# number of threads to use(1)
--threads: 1, 50, 100

# Storage engine, only innodb support transaction(innodb)
--mysql-storage-engine: innodb

# 5M, 10M, 20M, 50M 100M
--innodb-buffer-pool-size: 5242880, 2147483648, 4294967296

# Do not change this 2 configurations unless you encounter errors about them
--innodb-log-file-size: 200M
--thread-concurrency: 2000


###########################
###       models        ###
###########################

{--table-size, --threads, --innodb-buffer-pool-size} @ 3
```
Note that `--table-size`, `--threads` are parameters of `sysbench`

Then, run
```bash
./pict conf_variable_and_values.txt > mariadb_sample_result.txt
```

### Finally

run：

`python PerfTest_dbs.py`

result will be shown in `mariadb_sample_result`