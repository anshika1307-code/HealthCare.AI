
# System Design for Healthcare AI

## Basic Workflow
user query -> query processing -> retrieve related information -> build context with user query -> ask llm -> response -> score it -> send back to user

request -> fast api with async handler -> trigger langgraph orchestration pipeline (query node, retrieve node, rerank node, context node, generate node, confidence node, response node)

## Data Ingestion Pipeline
(Runs as a batch job, decoupled from other layers, pipeline is idempotent — reingestion safe)
- accept data [continuous, schedule, static] [different types of format]
- data parsing [raw data]
- quality checking of this data [complex formats, unstructured, structured]
- preprocessing of data (refinement of data)
- split into chunks
- convert into vectors (embedding)
- store in VectorDB

## Retrieval Pipeline

- receive user query
- preprocess query
- convert into embedding
- search in vectorDB
- put the responses into list according to the score

## Augmentation
- rerank the responses and filter top k response
- integrate the list of responses (context) and user query
- prepare a prompt with context and user query for llm
- get response from llm
- send back to user

## Retry logic
- 3 times retry with standard time gap, on third failure send user a degraded message with sources only

## Potential Failing points

user side
- Qdrant server down — return failure message with reason
- LLM rate limit / timeout — retry 3 times, otherwise give degraded answer with only sources
- LLM low confidence score — return answer with warning

other
- Embedder timeout — retry once, fail ingestion batch gracefully
- CI evaluation fails due to low score — block deployment (GitHub Actions)
- New document ingestion with higher drift score — alert and seek approval before merging in existing ingestion

**Note:** For all failing points prepare detection


## Observability
- Dashboard (latency / faithfulness / query volume / drift score)
- Alert: drift_score > threshold → email notification

## CI/CD & Evaluation

- GitHub push ──► lint ──► unit tests ──► integration tests
               ──► run_eval.py (30 questions)
               ──► faithfulness < threshold → BLOCK DEPLOY
               ──► faithfulness ≥ threshold → auto-deploy (Railway)
