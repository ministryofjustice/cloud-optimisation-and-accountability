
Apache Spark job to generate monthly csv reports of costs per namespace and account

`mvn clean package`

Expects the input to be CUR v2 files at Parquet format in a directory `BILLING_PERIOD=$billingPeriod`.
Generates 2 CSV files with the costs aggregated per product.

cp target/coat-reports-1.0.jar ../../output

docker run -it -v /Users/julien.nioche/data/curs:/curs -v /Users/julien.nioche/data/output:/output  apache/spark:3.5.5-java17 \
/opt/spark/bin/spark-submit  \
--class ProcessParquetApp \
--master 'local[*]' \
/output/coat-reports-1.0.jar \
/curs /output 2025-04

