
docker run -it -v /Users/julien.nioche/data/curs:/curs -v /Users/julien.nioche/data/output:/output  apache/spark:3.5.5-java17 \
 /opt/spark/bin/spark-shell -i output/script.scala

docker run -it -v /Users/julien.nioche/data/curs:/curs -v /Users/julien.nioche/data/output:/output  apache/spark:3.5.5-java17 \
/opt/spark/bin/spark-submit  \
--class ProcessParquetApp \
--master 'local[*]' \
/output/coat-reports-1.0.jar \
/curs /output/test

