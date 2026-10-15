import os
import sys
import logging
from typing import Optional
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

def configure_spark_environment() -> None:
    """
    Configures environment variables required for PySpark on Windows.
    Ensures JAVA_HOME and Python worker paths are set correctly.
    """
    # 1. Configure JAVA_HOME if not valid
    java_home = os.environ.get("JAVA_HOME")
    default_jdk = r"C:\Program Files\Java\jdk-21.0.12"
    if not java_home or not os.path.exists(java_home):
        if os.path.exists(default_jdk):
            os.environ["JAVA_HOME"] = default_jdk
            logger.info(f"Set JAVA_HOME to installed JDK: {default_jdk}")
        elif os.path.exists(r"C:\Program Files\Java\latest"):
            os.environ["JAVA_HOME"] = r"C:\Program Files\Java\latest"
            logger.info("Set JAVA_HOME to C:\\Program Files\\Java\\latest")

    # 2. Configure Python executable for PySpark driver & workers
    python_exe = sys.executable
    os.environ["PYSPARK_PYTHON"] = python_exe
    os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

def get_spark_session(app_name: str = "TravelWise-ETL") -> SparkSession:
    """
    Creates and returns a local SparkSession optimized for lightweight, reliable ETL execution.
    """
    configure_spark_environment()

    spark = SparkSession.builder \
        .appName(app_name) \
        .master("local[2]") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .config("spark.driver.host", "localhost") \
        .config("spark.ui.enabled", "false") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.default.parallelism", "2") \
        .getOrCreate()

    # Set log level to reduce console noise
    spark.sparkContext.setLogLevel("WARN")
    return spark
