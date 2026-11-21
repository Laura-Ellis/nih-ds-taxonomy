"""Shared pieces for ranking NIH funding calls (NOFOs) for a project: load and parse targeted NOFOs, score
project text against every NOFO, check project details (activity code, institute, fiscal years), and build
learning-to-rank features. Used by analyses/topics/nofo_link_ltr.py; nofo_match_ltr.py has the same steps inline.

    tg = load_targeted(ROOT / "data" / "raw" / "nofo")
    scorer = TextScorer(tg, fit_text)            # fit word weights once
    S = scorer.scores(text, titles)               # name -> projects x NOFOs
    D = details(projects, tg)                     # name -> projects x NOFOs
    X, names, cand = features(S, D, k=150)        # projects x k x features, candidate NOFO indexes
"""

import re

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

IC = {"NCI": "CA", "NIAID": "AI", "NIGMS": "GM", "NHLBI": "HL", "NIA": "AG", "NINDS": "NS", "NIDDK": "DK", "NIMH": "MH",
      "NICHD": "HD", "NIDA": "DA", "NIAAA": "AA", "NIEHS": "ES", "NHGRI": "HG", "NEI": "EY", "NIBIB": "EB", "NLM": "LM",
      "NIAMS": "AR", "NIDCR": "DE", "NIDCD": "DC", "NINR": "NR", "NIMHD": "MD", "NCCIH": "AT", "NCCAM": "AT",
      "NCATS": "TR", "FIC": "TW", "OD": "OD", "NCRR": "RR", "ORIP": "OD"}
NOFO_RE = r"(?:RFA|PAR|PAS|PA|NOT)-[A-Z0-9]+-\d+(?:-\d+)?"
TEXT = ["TF-IDF", "TF-IDF, best chunk", "TF-IDF, 1-3 word phrases", "BM25", "BM25, best chunk", "Title match"]
RAW = ["TF-IDF", "BM25, best chunk", "Title match"]


def kind(n):
    return "Targeted (RFA)" if n.startswith("RFA") else "Targeted (PAR)" if n.startswith("PAR") else \
        "Parent and other PA" if n.startswith("PA") else "Other"


def _between(t, a, z, cap=600):
    i = t.find(a)
    if i < 0:
        return ""
    j = t.find(z, i + len(a))
    return t[i + len(a): j if j > 0 else i + cap]


def load_targeted(nofo_dir):
    """Targeted NOFOs (RFA, PAR) with Section I text, title, activity codes, institutes, open and expiration years."""
    man = pd.read_csv(nofo_dir / "manifest.csv").drop_duplicates("nofo", keep="last")
    nofos = man[man.status == 200][["nofo"]].copy()
    read = lambda f: f.read_text(encoding="utf-8", errors="ignore") if f.exists() else ""  # noqa: E731
    nofos["text"] = [read(nofo_dir / "section1" / f"{n}.txt") for n in nofos.nofo]
    nofos = nofos[nofos.text.str.len() > 200].reset_index(drop=True)
    tg = nofos[nofos.nofo.map(kind).str.startswith("Targeted")].reset_index(drop=True)
    rows = []
    for x in tg.nofo:
        t = read(nofo_dir / "text" / f"{x}.txt")
        acts = set(re.findall(r"\b([A-Z]{1,2}\d[0-9A-Z])\b", _between(t, "Activity Code", "Announcement Type")[:400]))
        parts = _between(t, "Components", "Funding Opportunity Title")
        ics = {IC[a] for a in re.findall(r"\(([A-Z]{2,6})\)", parts) if a in IC}
        m = re.match(r"(?:RFA|PAR|PAS|PA)-([A-Z]{2})-\d{2}-", x)
        if m:
            ics.add(m.group(1))                      # issuing institute from the NOFO number
        if "Common Fund" in parts or "Roadmap" in parts:
            ics |= {"OD", "RM"}
        yr = re.search(r"-(\d{2})-", x)
        ny = 2000 + int(yr.group(1)) if yr else None
        o = re.findall(r"\b(?:19|20)\d\d\b", _between(t, "Open Date", "\n\n\n")[:120])
        e = re.findall(r"\b(?:19|20)\d\d\b", _between(t, "Expiration Date", "\n\n\n")[:120])
        rows.append({"title": re.sub(r"\s+", " ", _between(t, "Funding Opportunity Title", "Activity Code")).strip(),
                     "acts": acts, "ics": ics, "issuer": m.group(1) if m else "",
                     "open": int(o[0]) if o else ny, "exp": int(e[0]) if e else (ny + 3 if ny else None)})
    return pd.concat([tg, pd.DataFrame(rows)], axis=1)


def zrows(s):
    """Standardize each row (each project's scores across NOFOs)."""
    return (s - s.mean(1, keepdims=True)) / (s.std(1, keepdims=True) + 1e-9)


class TextScorer:
    """Word-matching scores of project text against every targeted NOFO (whole text, best 200-word chunk, phrases,
    BM25, and title). Word weights are fit once on the NOFO text plus a sample of project text."""

    def __init__(self, tg, fit_text, fit_titles):
        self.m = len(tg)
        w = [t.split() for t in tg.text]
        ch = pd.DataFrame([(i, " ".join(x[s:s + 200])) for i, x in enumerate(w) for s in range(0, max(len(x), 1), 200)],
                          columns=["nofo_idx", "text"])
        self.starts = np.r_[0, np.flatnonzero(np.diff(ch.nofo_idx.to_numpy())) + 1]
        both = pd.concat([pd.Series(fit_text), tg.text])
        self.tf = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.5, sublinear_tf=True).fit(both)
        self.tf_doc, self.tf_chunk = self.tf.transform(tg.text), self.tf.transform(ch.text)
        self.tf3 = TfidfVectorizer(stop_words="english", ngram_range=(1, 3), min_df=2, max_df=0.5, sublinear_tf=True).fit(both)
        self.tf3_doc = self.tf3.transform(tg.text)
        self.bm_cv, self.bm_doc = self._bm25(tg.text, fit_text)
        self.bmc_cv, self.bm_chunk = self._bm25(ch.text, fit_text)
        self.tt = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(list(tg.title) + list(fit_titles))
        self.tt_doc = self.tt.transform(tg.title)

    @staticmethod
    def _bm25(docs, extra, k1=1.2, b=0.75):
        cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, max_df=0.5).fit(
            pd.concat([pd.Series(list(docs)), pd.Series(list(extra))]))
        D = cv.transform(docs).astype(np.float32).tocoo()
        dl = np.asarray(D.tocsr().sum(1)).ravel()
        df = np.bincount(D.col, minlength=D.shape[1])
        idf = np.log(1 + (D.shape[0] - df + 0.5) / (df + 0.5)).astype(np.float32)
        w = D.data * (k1 + 1) / (D.data + k1 * (1 - b + b * dl[D.row] / dl.mean())) * idf[D.col]
        return cv, sparse.csr_matrix((w, (D.row, D.col)), shape=D.shape).T.tocsr()

    def _chunk_max(self, Q, C):
        return np.maximum.reduceat((Q @ C.T).toarray(), self.starts, axis=1).astype(np.float32)

    def _binary(self, cv, text):
        Q = cv.transform(text).astype(np.float32)
        Q.data[:] = 1
        return Q.tocsr()

    def scores(self, text, titles):
        text, titles = list(text), list(titles)
        Qt = self.tf.transform(text)
        return {"TF-IDF": (Qt @ self.tf_doc.T).toarray().astype(np.float32),
                "TF-IDF, best chunk": self._chunk_max(Qt, self.tf_chunk),
                "TF-IDF, 1-3 word phrases": (self.tf3.transform(text) @ self.tf3_doc.T).toarray().astype(np.float32),
                "BM25": (self._binary(self.bm_cv, text) @ self.bm_doc).toarray().astype(np.float32),
                "BM25, best chunk": np.maximum.reduceat((self._binary(self.bmc_cv, text) @ self.bm_chunk).toarray(),
                                                        self.starts, axis=1).astype(np.float32),
                "Title match": (self.tt.transform(titles) @ self.tt_doc.T).toarray().astype(np.float32)}


def details(projects, tg):
    """Project-detail checks against every NOFO: activity code allowed, institute issues or joins, open in a
    funding year (open year to expiration year + 2) and years off if not, plus NOFO traits."""
    n, m = len(projects), len(tg)
    act_ok, ic_ok, fy_ok = (np.ones((n, m), np.int8) for _ in range(3))
    fy_gap = np.zeros((n, m), np.float32)
    o, e = tg.open.fillna(0).to_numpy(), tg.exp.fillna(9999).to_numpy()
    for i, (a, c, f) in enumerate(zip(projects.activity, projects.administering_ic, projects.fiscal_years)):
        if isinstance(a, str) and a:
            act_ok[i] = [not s or a in s for s in tg.acts]
        if isinstance(c, str) and c:
            ic_ok[i] = [not s or c in s for s in tg.ics]
        fy = np.array(sorted({int(y) for y in re.findall(r"\d{4}", str(f))}))[:, None]
        if fy.size:
            inside = ((fy >= o) & (fy <= e + 2)).any(0)
            fy_ok[i] = inside
            fy_gap[i] = np.where(inside, 0, np.minimum(np.abs(fy - o), np.abs(fy - e - 2)).min(0))
    rep = lambda v: np.broadcast_to(np.asarray(v, np.float32), (n, m))  # noqa: E731
    return {"Activity code allowed": act_ok, "Institute issues or joins": ic_ok, "Open in a funding year": fy_ok,
            "Years from open window": fy_gap, "RFA (vs. PAR)": rep(tg.nofo.str.startswith("RFA")),
            "Number of activity codes": rep(tg.acts.str.len()), "Number of institutes": rep(tg.ics.str.len())}


def features(S, D, k=150):
    """Candidates (top k by average word-matching score, NOFOs passing the activity code and institute filters
    first) and their learning-to-rank features. Returns X (projects x k x features), names, candidate indexes, prior."""
    Z = {name: zrows(S[name]) for name in TEXT}
    prior = (Z["TF-IDF"] + Z["BM25, best chunk"]) / 2
    prior = np.where((D["Activity code allowed"] & D["Institute issues or joins"]).astype(bool), prior, prior - 100)
    cand = np.argsort(-prior, axis=1)[:, :k]
    feats = {f"{name} (z)": Z[name] for name in TEXT} | {f"{name} (raw)": S[name] for name in RAW} | D
    rr = np.arange(len(cand))[:, None]
    X = np.stack([f[rr, cand] for f in feats.values()], -1).astype(np.float32)
    return X, list(feats), cand, prior
