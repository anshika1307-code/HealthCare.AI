# Eval Question Format — to generate Q&As for evaluation
> Format: question | expected_answer_contains | source_doc | section | difficulty
> Should cover maximun edge cases
> minimum 15 questions for each document -(50% hard, 35% medium, 15% easy)
> look for the sections where the chunking can break the context - build some uestions to test those edge cases
> look for noise in documents and try to generate questions that can lead to hallucinations or missings
> look for tables and figures, questions can be asked from them too.
> look at the structure of documents and try to generate questions that can test the cross-document understanding
> Also test with difficult to understand questions as well

## Questions — Doc 1: metformin_fda_label.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |

## Questions — Doc 2: ada_standards_care_diabetes_6.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |

## Questions — Doc 3: ada_standards_care_diabetes_9.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |

## Questions — Doc 4: jnc8_guidelines_management_hypertension_original.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |

## Questions - (Out of scope) - system should say "insufficient context" or "information not available"

| # | question | why this fails | expected response | expected confidence score |
|---|----------|----------------------------|------------|---------|------------|---------|
| 1 |  |  |  |  |  |  |  |

# Questions for testing cross document understanding
| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |  |

# Questions for Evaluating chunking size (not to small or not to big, not overlapping too much)

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |  |

# Questions for testing normalization
| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|----------------------------|------------|---------|------------|
| 1 |  |  |  |  |  |  |  |


## How to use them
- write a script to convert it in json format and feed it to RAGAS for evaluation and CI Pipeline
- format
   eval_set = [
    {
        "question": "What is the recommended...",
        "ground_truth": "metformin is contraindicated in CKD stage 3-5",
        "source_doc": "nih_diabetes_guidelines.pdf",
        "section": "treatment_recommendations",
        "difficulty": "hard"
    }
    # ... 
    ]


## Next Steps
- ask AI to generate minimum 15 questions for each document (keeping in mind all the above instructions and same format keep it in new file eval_questions.md and save it in json format too in Evaluation folder)



