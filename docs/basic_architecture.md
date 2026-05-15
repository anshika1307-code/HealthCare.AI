
# System Design for Healthcare AI

## Basic Workflow
user uery -> uery processing -> retrieve related information -> build context with user uery -> ask llm -> response -> score it -> send back to user

reuest -> fast api with async handler -> trigger langgraph orchestration pipeline (uery node, retrieve node, rerank node, context node, generate node, confidence node, response node)

## Data Ingestion Pipeline
(Runs as a batch job, decoupled from other layers, pipeline is idempotent:- reingestion)
- accept data [continous, schedule, static] [different types of format] 
- data parsing [raw data]
- uality checking of this data [complex formats, unstructured, structure]
- preprocessing of data ( refinement of data)
- Split into chunks
- convert into vectors(embedding)
- store in VectorDB

## Retrieval Pipeline

- recieve user uery
- preprocess uery
- convert into embedding
- search in vectorDB 
- put the responses into list according to the score

## Augmentation
- Rerank the responses and filter top k response
- integrate the  list of responses (context) and user uery
- prepare a prompt with context and user uery for llm
- get response from llm
- send back to user

## Retry logic
- 3 times retry with standard time gap, on third failure send user a degraded message with sources only

## Potential Failing points

user side
- Qdrant server down - Return failure message with reason
- LLM rate limit/ timeout - retry 3 times otherwise give degraded answer with only sources
- LLM low confidence score - Return answer with warning

other
- Embedder timeout - retry once, fail ingestion batch gracefully
- CI evaluation fails due to less score - block deployment (GIthub Action)
- New document ingestion with higher drift score - alert and seek approval before merging in existing ingestion.

**Note:** For all failing points prepare detection


## Observability
- Dashboard (latency / faithfulness / query volume / drift score)
- Alert: drift_score > threshold → email notification

## CI/CD & EVALUATION

- GitHub push ──► lint ──► unit tests ──► integration tests  
               ──► run_eval.py (50 questions) 
               ──► faithfulness < threshold → BLOCK DEPLOY
              ──► faithfulness ≥ threshold → auto-deploy (Render or any free tool)
