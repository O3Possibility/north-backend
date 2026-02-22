"""
Index your UTCP table into ChromaDB for NORTH.

Usage (from backend/):
  python scripts/index_db.py --csv MASTER_CANONICAL.csv

Required columns:
  ID_MASTER, Framework_Name, Core_Triad, Blurb
Recommended metadata columns:
  Regime_Type, Macro_Region, Lineage_Cluster, Parse_Flag
"""

import argparse
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from app.config import settings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to MASTER_CANONICAL.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)

    client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    col = client.get_or_create_collection(name=settings.COLLECTION_NAME, embedding_function=emb_fn)

    documents, metadatas, ids = [], [], []
    for _, row in df.iterrows():
        content = (
            f"Framework: {row.get('Framework_Name','')}. "
            f"Core Triad: {row.get('Core_Triad','')}. "
            f"Blurb: {row.get('Blurb','')}"
        )
        documents.append(content)
        metadatas.append({
            "Framework_Name": str(row.get("Framework_Name","")),
            "Core_Triad": str(row.get("Core_Triad","")),
            "Regime_Type": str(row.get("Regime_Type","")),
            "Macro_Region": str(row.get("Macro_Region","")),
            "Lineage_Cluster": str(row.get("Lineage_Cluster","")),
            "Parse_Flag": str(row.get("Parse_Flag","")),
        })
        ids.append(str(row.get("ID_MASTER","")))

    col.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Success: indexed {len(documents)} frameworks into {settings.CHROMA_PATH}")

if __name__ == "__main__":
    main()
