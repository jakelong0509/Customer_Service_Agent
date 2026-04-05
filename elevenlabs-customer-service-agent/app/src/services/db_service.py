from pathlib import Path

from src.infrastructure.database import get_connection
from src.utils.RRFLoader import RRFLoader


class DBService:
  def __init__(
    self
  ):
    pass

  async def ingest_local(
    self,
    file_path: str,
    table_name: str,
    columns: list[str],
    batch_size: int = 128
  ) -> None:
    """
    Ingest a local file into the database using COPY per chunk (asyncpg copy_records_to_table).
    Args:
      file_path: Path to the file to ingest.
      table_name: Destination table name (trusted identifier; not user-facing input).
      columns: Column names in file order; must match the target table columns for COPY.
      batch_size: Number of rows per read chunk / COPY batch.
    """
    assert table_name != "", "Table name cannot be empty."
    assert batch_size > 0, "Batch size must be greater than 0."
    assert file_path != "", "File path cannot be empty."
    assert columns, "columns must be non-empty and match the RRF field order and DB table."

    if Path(file_path).suffix == ".RRF":
      loader = RRFLoader(filePath=file_path, columns=columns, batchSize=batch_size)
    else:
      raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")

    chunk_stream = loader.lazy_load()
    async with get_connection() as conn:
      for chunk in chunk_stream:
        if not chunk:
          continue
        records = [tuple(row[c] for c in columns) for row in chunk]
        await conn.copy_records_to_table(
          table_name,
          records=records,
          columns=columns,
        )
