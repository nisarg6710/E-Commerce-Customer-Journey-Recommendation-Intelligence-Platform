import os
import sys

# Change the notebook's active working directory to the project root
if os.path.basename(os.getcwd()) == "tests":
    os.chdir("..")

# Ensure the root path is also in sys.path
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
import os

from dotenv import load_dotenv
from databricks import sql

load_dotenv()

server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
http_path = os.getenv("DATABRICKS_HTTP_PATH")
access_token = os.getenv("DATABRICKS_TOKEN")

if not all([server_hostname, http_path, access_token]):
    raise ValueError(
        "Missing Databricks configuration. "
        "Check DATABRICKS_SERVER_HOSTNAME, "
        "DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN in .env."
    )

print("Configuration loaded.")

try:
    with sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("Basic SQL connection successful:", result[0])

            cursor.execute("""
                SELECT COUNT(*) AS table_count
                FROM system.information_schema.tables
                WHERE table_catalog = 'ecommerce_intelligence'
                  AND table_schema = 'gold'
            """)
            table_count = cursor.fetchone()[0]
            print("Gold tables visible:", table_count)

except Exception as exc:
    print("Connection test failed.")
    print("Error type:", type(exc).__name__)
    print("Error details:", str(exc))
    raise
