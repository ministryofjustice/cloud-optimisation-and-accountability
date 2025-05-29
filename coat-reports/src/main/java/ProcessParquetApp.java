import org.apache.spark.sql.*;
import org.apache.spark.sql.expressions.UserDefinedFunction;
import org.apache.spark.sql.types.DataTypes;
import static org.apache.spark.sql.functions.*;

public class ProcessParquetApp {

    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("Usage: ProcessParquetApp <inputPath> <outputPath> <billing_period> [byAccount]");
            System.exit(1);
        }

        String inputPath = args[0];
        String outputPath = args[1];
        String billingPeriod = args[2];

        // TODO check format YYYY-MM

        outputPath+="/"+billingPeriod+"/";

        inputPath += "/BILLING_PERIOD="+billingPeriod;

        SparkSession spark = SparkSession.builder().config("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")
                .appName("ProcessParquetApp")
                .master("local[*]")
                .getOrCreate();

        // Read the input Parquet file
        Dataset<Row> parquetFileDF = spark.read().parquet(inputPath);

            // Select and filter the relevant columns
            Dataset<Row> selectedDF = parquetFileDF.select(
                    col("line_item_usage_account_id").alias("account_id"),
                    col("product").getItem("product_name").alias("product_name"),
                    col("line_item_unblended_cost").alias("cost")
            );

            // Group by and aggregate
            Dataset<Row> groupedDF = selectedDF.groupBy("account_id", "product_name")
                    .agg(sum("cost").alias("total_unblended_cost")).withColumn("total_unblended_cost", round(col("total_unblended_cost"), 2));

            // Sort the output
            Dataset<Row> sortedDF = groupedDF.orderBy(
                    asc("account_id"),
                    desc("total_unblended_cost")
            );

            // Write the result to a single CSV file
            sortedDF.coalesce(1)
                    .write()
                    .option("header", "true")
                    .mode(SaveMode.Overwrite)
                    .csv(outputPath+"costs_by_account_id");

        // Select and filter the relevant columns
        Dataset<Row> selectedDF2 = parquetFileDF.select(
                col("resource_tags").getItem("user_namespace").alias("user_namespace"),
                col("product").getItem("product_name").alias("product_name"),
                col("line_item_unblended_cost").alias("cost")
        ).filter(
                col("user_namespace").isNotNull()
                        .and(length(col("user_namespace")).gt(0))
        );

        // Group by and aggregate
        Dataset<Row> groupedDF2 = selectedDF2.groupBy("user_namespace", "product_name")
                .agg(sum("cost").alias("total_unblended_cost")).withColumn("total_unblended_cost", round(col("total_unblended_cost"), 2));;

        // Sort the output
        Dataset<Row> sortedDF2 = groupedDF2.orderBy(
                asc("user_namespace"),
                desc("total_unblended_cost")
        );

            // Write the result to a single CSV file
            sortedDF2.coalesce(1)
                    .write()
                    .option("header", "true")
                    .mode(SaveMode.Overwrite)
                    .csv(outputPath+"costs_by_namespace");

        spark.stop();
    }
}
