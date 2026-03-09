"""
CSV Processor Cloud Function - Week 5
Triggered by CSV uploads to GCS, loads data into BigQuery.
"""

import functions_framework
from google.cloud import bigquery, storage
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
bq_client = bigquery.Client()
storage_client = storage.Client()

# BigQuery configuration
PROJECT_ID = "botpproject"
DATASET_ID = "csv_data"


def ensure_dataset_exists():
    """Create dataset if it doesn't exist"""
    try:
        dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        bq_client.create_dataset(dataset, exists_ok=True)
        logger.info(f"Dataset {dataset_id} ready")
    except Exception as e:
        logger.error(f"Dataset creation failed: {e}")
        raise


@functions_framework.cloud_event
def process_csv(cloud_event):
    """
    Triggered by GCS finalize event.
    Loads CSV from GCS into BigQuery.
    
    Event format:
    {
        "bucket": "bucket-name",
        "name": "path/to/file.csv",
        ...
    }
    """
    try:
        data = cloud_event.data
        bucket_name = data["bucket"]
        file_name = data["name"]
        
        logger.info(f"Processing CSV: gs://{bucket_name}/{file_name}")
        
        # Only process CSV files
        if not file_name.lower().endswith('.csv'):
            logger.info(f"Skipping non-CSV file: {file_name}")
            return
        
        # Ensure dataset exists
        ensure_dataset_exists()
        
        # Generate table name from filename
        table_name = file_name.split('/')[-1].replace('.csv', '').replace('-', '_').replace(' ', '_')
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
        
        # Load CSV into BigQuery
        uri = f"gs://{bucket_name}/{file_name}"
        
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,  # Auto-detect schema
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # Replace existing data
        )
        
        load_job = bq_client.load_table_from_uri(
            uri,
            table_id,
            job_config=job_config
        )
        
        load_job.result()  # Wait for job to complete
        
        # Get table info
        table = bq_client.get_table(table_id)
        
        logger.info(
            f"CSV loaded successfully: {table_name} "
            f"({table.num_rows} rows, {len(table.schema)} columns)"
        )
        
        return {
            "status": "success",
            "table": table_name,
            "rows": table.num_rows,
            "columns": len(table.schema)
        }
        
    except Exception as e:
        logger.error(f"CSV processing failed: {e}", exc_info=True)
        raise
