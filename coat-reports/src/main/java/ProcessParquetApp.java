import org.apache.spark.sql.*;
import org.apache.spark.sql.expressions.UserDefinedFunction;
import org.apache.spark.sql.types.DataTypes;
import static org.apache.spark.sql.functions.*;

public class ProcessParquetApp {

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: ProcessParquetApp <inputPath> <outputPath>");
            System.exit(1);
        }

        String inputPath = args[0];
        String outputPath = args[1];

        SparkSession spark = SparkSession.builder()
                .appName("ProcessParquetApp")
                .master("local[*]")
                .getOrCreate();

        // Read the input Parquet file
        Dataset<Row> parquetFileDF = spark.read().parquet(inputPath);

        // Select and filter the relevant columns
        Dataset<Row> selectedDF = parquetFileDF.select(
                col("resource_tags").getItem("user_namespace").alias("user_namespace"),
                col("product").getItem("product_name").alias("product_name"),
                col("line_item_unblended_cost").alias("cost")
        ).filter(
                col("user_namespace").isNotNull()
                        .and(length(col("user_namespace")).gt(0))
                        .and(col("cost").gt(0))
        );

        // Group by and aggregate
        Dataset<Row> groupedDF = selectedDF.groupBy("user_namespace", "product_name")
                .agg(sum("cost").alias("total_unblended_cost")).withColumn("total_unblended_cost", round(col("total_unblended_cost"), 2));;

        // Sort the output
        Dataset<Row> sortedDF = groupedDF.orderBy(
                asc("user_namespace"),
                desc("total_unblended_cost")
        );

        // Write the result to a single CSV file
        sortedDF.coalesce(1)
                .write()
                .option("header", "true")
                .mode(SaveMode.Overwrite)
                .csv(outputPath);

        spark.stop();
    }
}
