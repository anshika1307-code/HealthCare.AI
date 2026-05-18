# Observibility Specification
> Per-query faithfulness, latency by stage, RRF scores, reranker delta, embedding drift on every batch. Query text never logged (PHI risk).

## RAG Matrics logic

- RAGMetrics Pseudocode:   
  - record(query_id, latency, faithfulness, doc_ids)
  - writes to Redis sorted set:    key=metrics:latency, 
- score=timestamp, 
- value=latency_value 



## Drift Detector logic

- DriftDetector Pseudocode :   
  - on_new_batch(embeddings) → compute centroid   
  - compare to baseline centroid in Redis   
  - return 1 - cosine_similarity(new, baseline) 
- drift_score = 1 - (A·B / |A||B|)
- 0 = identical, 1 = completely different
- threshold: 0.15 (Why - conservative — we rather alert more than miss a real drift)


