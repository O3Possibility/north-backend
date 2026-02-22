import random
import numpy as np
import chromadb
from chromadb.utils import embedding_functions
from app.config import settings

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 1.0
    return float(1.0 - (np.dot(a, b) / denom))

class ConscienceChordEngine:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.emb_fn
        )

    def _embed(self, text: str) -> np.ndarray:
        vec = self.emb_fn([text])[0]
        return np.array(vec, dtype=np.float32)

    def get_tonic(self, prompt: str):
        res = self.collection.query(query_texts=[prompt], n_results=settings.TONIC_K)
        tonic_id = res["ids"][0][0]
        tonic_doc = res["documents"][0][0]
        tonic_meta = res["metadatas"][0][0]
        return tonic_id, tonic_doc, tonic_meta

    def _candidate_pool(self, prompt: str, pool_k: int):
        res = self.collection.query(query_texts=[prompt], n_results=pool_k)
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        return list(zip(ids, docs, metas))

    def _pick_one_by_filter(self, candidates, where: dict):
        hits = []
        for cid, doc, meta in candidates:
            ok = True
            for k, v in where.items():
                if str(meta.get(k, "")) != str(v):
                    ok = False
                    break
            if ok:
                hits.append((cid, doc, meta))
        return random.choice(hits) if hits else None

    def _pick_diverse_max_distance(self, tonic_vec, candidates, n, already_chosen=None):
        chosen = list(already_chosen) if already_chosen else []
        used = {k: set() for k in settings.DIVERSITY_KEYS}
        for _, _, meta in chosen:
            for k in settings.DIVERSITY_KEYS:
                used[k].add(meta.get(k, ""))

        def accept(meta):
            if not settings.ENFORCE_DIVERSITY:
                return True
            for k in settings.DIVERSITY_KEYS:
                v = meta.get(k, "")
                if v and v in used[k]:
                    return False
            return True

        scored = []
        for cid, doc, meta in candidates:
            vec = self._embed(doc)
            d = cosine_distance(tonic_vec, vec)
            scored.append((d, cid, doc, meta))
        scored.sort(reverse=True, key=lambda x: x[0])

        for d, cid, doc, meta in scored:
            if len(chosen) >= n:
                break
            if accept(meta):
                chosen.append((cid, doc, meta))
                for k in settings.DIVERSITY_KEYS:
                    used[k].add(meta.get(k, ""))

        if len(chosen) < n:
            for d, cid, doc, meta in scored:
                if len(chosen) >= n:
                    break
                if any(cid == c[0] for c in chosen):
                    continue
                chosen.append((cid, doc, meta))

        return chosen[:n]

    def get_chord(self, user_prompt: str, ballast_pool_k: int | None = None):
        tonic_id, tonic_doc, tonic_meta = self.get_tonic(user_prompt)
        tonic_regime = str(tonic_meta.get("Regime_Type", "")).strip()
        tonic_vec = self._embed(tonic_doc)

        pool_k = ballast_pool_k if ballast_pool_k is not None else settings.BALLAST_POOL_K
        pool = self._candidate_pool(user_prompt, pool_k)
        pool = [(cid, doc, meta) for (cid, doc, meta) in pool if cid != tonic_id]

        selected = []

        # If tonic is torsional: force ballast regime spread (Branching + Gradient if possible)
        if tonic_regime == "Torsional":
            b = self._pick_one_by_filter(pool, {"Regime_Type": "Branching"})
            if b:
                selected.append(b)
                pool = [(cid, doc, meta) for (cid, doc, meta) in pool if cid != b[0]]
            g = self._pick_one_by_filter(pool, {"Regime_Type": "Gradient"})
            if g:
                selected.append(g)
                pool = [(cid, doc, meta) for (cid, doc, meta) in pool if cid != g[0]]
            selected = self._pick_diverse_max_distance(tonic_vec, pool, settings.BALLAST_N, selected)
        else:
            # otherwise: guarantee at least one torsional ballast (kit flag or regime)
            t = self._pick_one_by_filter(pool, {"Parse_Flag": settings.TORSION_PARSE_FLAG})
            if t is None:
                t = self._pick_one_by_filter(pool, {"Regime_Type": "Torsional"})
            if t:
                selected.append(t)
                pool = [(cid, doc, meta) for (cid, doc, meta) in pool if cid != t[0]]
            selected = self._pick_diverse_max_distance(tonic_vec, pool, settings.BALLAST_N, selected)

        return {
            "tonic": {"id": tonic_id, "doc": tonic_doc, "meta": tonic_meta},
            "ballasts": [{"id": cid, "doc": doc, "meta": meta} for (cid, doc, meta) in selected],
        }
