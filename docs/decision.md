# Decisions - For Overall Project

## Data Source
  - Document used -  the metformin FDA prescribing label, the ADA Standards of Care in Diabetes 2023 (Sections 6 and 9), and the JNC 8 hypertension management guidelines.
  - Why - 
    1. Overlapping topics
    2. Different structure and style
    3. have lots of noise
    4. need to stress test retrieval challenges

## Data Input Method

   - load using langchain
   - Reason - data sources stays in database/codebase for this prototype


## Data Preprocessing Method
   
   - Custom Cleaner
   - Reason - we had taken noisy documents, also lesser in number so with custom preprocessing we can refine the documents more precisely by manually evaluating documents
   - Need to remove - headers, footer, page numbers, reference
   - Need to handle - proper section extraction, tables

## Data Extraction from PDFs

 - Lib - PyMuPDF (faster for bulk extraction) and pdfplumber (better for table extraction)
 
## Data chunking

  - Not using semantic chunking - as for these documents rule-based section detection is both faster and more accurate
  - 512-token chunks with 64-token overlap, section-aware boundaries
  - How - used AI tools to analyse the documents and tell perfect chunk size and overlap size by document section length analysis, and will test 256/512/1024 and pick based on your eval scores(RAGAS) then MLflow to track these scores.


## Embedding Model

 - Decision: will take after testing two-three models on our documents and evaluating against evaluation uestions (BGE vs text-embedding-3-small)
 - use MLflow — Model Registry to track the experiment

## Vector Database

- Compared Qdrant, pinecone, & ChromaDB
- Decision: going with Qdrant
- why -
  1. Metadata filtering
  2. self hosted in docker


## Retrieval strategy
  
  - Decision - Hybrid Retrieval (Dense + BM25)
  - Reason - medical texts are full of acronyms so we keywords filtering(BM25) as well with searching by the meaning (dense) thats why lets use hybrid
  - take results from semantic search then scoring it with BM25 keywords freuency using RRF then use cross-encoder reranker to get top 5 for final context 
  - for transforming Queries - will use RRF (Reciprocal rank fusion)
  - will keep k=60 (best value as per the google search)
  - cross-encoder reranker for better context


## LLM

 - Cheaper GPT model
 - Reason - this is a prototype, need cost optimization but also show production level architecture
 - PROMPTING - we had to tell the model to answer only from the provided context, cite which document and section your answer comes from, and if the context does not contain sufficient information to answer, then say no explicitly rathen than fetching background knowledge.


## COnfidence scoring layer
 
 - we will set a confidence threshold according to evaluation results so that whenever the answer is below threshold we flag it to user with a warning along the answer.
 - better reliability and faithfullness
 - though increase latency a bit


## Orchestration

- Use - Langgraph Stategraph
- As we have multiple steps in our pipeline
- graph handles state, retries, and conditional routing between each nodes(components in our pipeline)
- easy debugging


## Serving layer

- Use - FastAPI + async
- As we allow multiple api calls at same time (concurrent users)


## Evaluation system - RAG

- Use - RAGAS
- Against a set of uestion prepared by me against expected answers - reading the document (covering edge cases and failing cases)
- Also with ai generated set of uestion by analysing the documents
- Faithfulness (did the answer come from the context?), Answer Relevancy (did it answer the question?), Context Precision, Context Recall.


## Testing
- Unit tests and integration tests
- for all the components of pipeline


## Drift Detection

- use - centroid cosine distance with threshold alert
- to detect the meaning drift of new documents from the existing documents, if this is greater than threshold, give alert so the answer uality does not decrease

## Other Tech Stack

- Python for backend
- Simple UI - AI generated
- Redis - store metrics for dashboard (not using the existing metrics tools, to get better understanding)
- Streamlit - dashboard + chat interface
- Docker + docker-compose
- CI/CD for ML (GitHub Actions) - demostrating how to handle production system deployment.

## Future Work

- I will run A/B evaluation on chunk size per document type and potentially use different chunking configs per ingestion pipeline. Can apply type-specific chunking config.
- Reranking adding latency, maybe in future we can change it with some better approach
- In production we should use Kubernetes instead of docker-compose
- Grafana for metrics
- Answer caching we can use later for cost optimization and fast retrieval for freuent ueries.

