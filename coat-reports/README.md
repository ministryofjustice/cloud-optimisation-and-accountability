
Apache Spark job to generate monthly csv reports of costs per namespace and account

Expects the input to be CUR v2 files at Parquet format in a directory `BILLING_PERIOD=$billingPeriod`.
Generates 2 CSV files with the costs aggregated per product as well as account id.

Build the Docker image with

`docker build -t coat-reports:1.0 .`

The command below processes the data locally by mounting the directories containing the CURs and output as volumes:

`docker run -it -v /Users/julien.nioche/data/curs:/curs -v /Users/julien.nioche/data/output:/output  coat-reports:1.0 \
/opt/spark/bin/spark-submit  \
--class ProcessParquetApp \
--master 'local[*]' \
/usr/local/lib/coat-reports-1.0.jar \
/curs /output 2025-04`

will generate 2 directories in the directory used for the output e.g.

```
2025-04
├── costs_by_account_id
    └── part-00000-97d4c7c3-17be-4209-a9b5-232a33d947d5-c000.csv
└── costs_by_namespace
    └── part-00000-2b212274-464a-43ce-975b-5d5a907d0f4c-c000.csv
```

Note that the names of the leaf files will change from one run to the other but they will get overwritten anyway.
What matters is that there will be a csv file with an arbitrary name under the 2 'cost_by_*' directories.

## TODO
- Add library and configuration to read from and write to S3 directly