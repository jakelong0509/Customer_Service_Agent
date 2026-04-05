import os
import pandas as pd
import gc
from tqdm import tqdm
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

class RRFLoader(BaseLoader):
  def __init__(self, filePath: str, columns: list[str], batchSize: int = 128):
    self._filePath = filePath
    self._columns = columns
    self._filename = os.path.basename(filePath).split(".")[0]
    self._batchSize = batchSize

  def lazy_load(self):
    chunk_iter = pd.read_csv(
      self._filePath,
      sep = "|",
      names=self._columns,
      dtype=str,
      chunksize=self._batchSize,
      low_memory= False,
      index_col=False
    )
    for chunk in tqdm(chunk_iter, desc=f"Loading Document {self._filename}"):
      chunk.fillna('', inplace=True)
      if len(self._columns) > 0:
        chunk = chunk.loc[:, self._columns]
      else:
        chunk = chunk.loc[:, :]
      chunk_docs = []
      for _, row in chunk.iterrows():
        chunk_docs.append(row)
      yield chunk_docs

      del chunk
      gc.collect()

  def load(self) -> list[Document]:
    return list(self.lazy_load())
  
  def _row_to_document(self, row: pd.Series) -> Document:
    content, metadata = self._content(row)
    return Document(page_content=content, metadata=metadata)
  
  def _content(self, row: pd.Series) -> str:
    parts = []
    metadata = {}
    for key, value in row.items():
      if value != '':
        parts.append(f"{key} : {value}")
        metadata[key] = value
    return "\n".join(parts), metadata

# if __name__ == "__main__":
#   loader = RRFLoader(filePath="D:/Medical_terms_codes/RxNORM/RXNCONSO.RRF", columns=["RXCUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "RXAUI", "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL", "SUPPRESS", "CVF"])
#   rxnconso = loader.load()

