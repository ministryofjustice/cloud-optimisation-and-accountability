import spark.implicits._
import org.apache.spark.sql.functions._

val parquetFileDF = spark.read.parquet("/curs");

val selectedDF = parquetFileDF.select(
  col("resource_tags").getItem("user_namespace").alias("user_namespace"),
  col("product").getItem("product_name").alias("product_name"),
  col("line_item_unblended_cost").alias("cost")
).filter(
  col("user_namespace").isNotNull &&
    length(col("user_namespace")) > 0 &&
    col("cost") =!= 0
  )

val groupedDF = selectedDF
  .groupBy("user_namespace", "product_name")
  .agg(
    sum("cost")
  )

val sortedDF = groupedDF.orderBy(
  asc("user_namespace"),
  desc("cost")
)

sortedDF
  .coalesce(1)  // reduce to a single partition to get one output CSV file
  .write
  .option("header", "true")  // include CSV header
  .mode("overwrite")
  .csv("/output/single_csv_output")
