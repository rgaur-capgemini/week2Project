"""
CSV Query Tool - Week 5
Query BigQuery tables created from CSV uploads.
"""

from typing import List
from google.cloud import bigquery
from app.agents.tools.base import BaseTool, ToolParameter, ToolResult
from app.logging_config import get_logger

logger = get_logger(__name__)


class CSVQueryTool(BaseTool):
    """Query CSV data stored in BigQuery"""
    
    def __init__(self):
        self.project_id = "botpproject"
        self.dataset_id = "csv_data"
        self.bq_client = bigquery.Client(project=self.project_id)
        logger.info("CSV query tool initialized")
    
    @property
    def name(self) -> str:
        return "csv_query"
    
    @property
    def description(self) -> str:
        return "Query CSV data from BigQuery tables. Tables are auto-created from CSV uploads. Use SQL SELECT statements."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="table_name",
                type="string",
                description="Table name (CSV filename without .csv extension)",
                required=True
            ),
            ToolParameter(
                name="query",
                type="string",
                description="SQL query (use SELECT statement). Table will be referenced automatically.",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum rows to return (default 100)",
                required=False,
                default=100
            )
        ]
    
    async def execute(self, table_name: str, query: str, limit: int = 100, **kwargs) -> ToolResult:
        try:
            logger.info(f"CSV query: table={table_name}, query='{query}'")
            
            # Build full table ID
            full_table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            
            # Add FROM clause if not present
            if "FROM" not in query.upper():
                query = f"{query} FROM `{full_table_id}`"
            else:
                # Replace table name with full ID
                query = query.replace(table_name, f"`{full_table_id}`")
            
            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            # Execute query
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            # Convert to list of dicts
            rows = [dict(row.items()) for row in results]
            
            return ToolResult(
                success=True,
                data={"rows": rows, "count": len(rows)},
                metadata={"table": table_name, "query": query}
            )
            
        except Exception as e:
            logger.error(f"CSV query failed: {e}")
            return ToolResult(success=False, error=str(e))
