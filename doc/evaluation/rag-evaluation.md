# RAG Evaluation Pipeline

Phase 4 evaluation framework for measuring retrieval-augmented generation quality and orchestration routing accuracy.

## Metrics

| Metric | Description |
|--------|-------------|
| **faithfulness** | Answer grounded in retrieved context |
| **answer_relevancy** | Answer addresses the question |
| **context_precision** | Retrieved context relevance |
| **context_recall** | Ground truth covered by context/answer |
| **hallucination** | Inverse grounding signal (lower is better) |
| **response_quality** | Weighted composite score |

Engines (automatic fallback chain):

1. **RAGAS** — when `ragas` is installed
2. **DeepEval** — when `deepeval` is installed and configured
3. **Heuristic** — always available (CI default)

## Run via CLI

From repo root:

```bash
cd backend
pip install -r requirements-dev.txt   # optional: ragas, deepeval
python ../eval/rag_eval.py --dataset ../eval/benchmark_dataset.json --output ../eval/reports
python ../eval/orchestration_eval.py --dataset ../eval/benchmark_dataset.json --output ../eval/reports
```

Using the unified runner:

```bash
cd backend
python -c "from evaluation.runner import run_evaluation; print(run_evaluation(engine_preference='heuristic'))"
```

## Run via API

**POST** `/evaluation/run` (JWT required)

```json
{
  "run_rag": true,
  "run_orchestration": true,
  "generate_answers": false,
  "engine_preference": "auto",
  "dataset_path": null
}
```

Response includes:

- `summary` — aggregate scores
- `rag_results` / `orchestration_results`
- `report_paths.json` and `report_paths.csv`

### Production access control

Set admin emails in Railway:

```env
EVAL_ADMIN_EMAILS=you@company.com,ops@company.com
```

In **development**, any authenticated user can run evaluation when `EVAL_ADMIN_EMAILS` is empty. In **production**, only listed emails are allowed.

## Sample dataset

Default benchmark: `backend/evaluation/datasets/sample_rag_eval.json`

Legacy dataset: `eval/benchmark_dataset.json`

**GET** `/evaluation/datasets/sample` — returns path and description.

## Reports

Reports are written to `eval/reports/`:

- `evaluation_YYYYMMDD_HHMMSS.json` — full report
- `evaluation_YYYYMMDD_HHMMSS.csv` — flat metrics for spreadsheets

## Install optional eval dependencies

```bash
pip install -r backend/requirements-dev.txt
```

Includes `ragas==0.1.24` and `deepeval==1.3.9`.

## Architecture

```
POST /evaluation/run
       ↓
evaluation/runner.py
       ├── metrics.py (RAGAS → DeepEval → heuristic)
       ├── orchestrator routing checks
       └── exporters.py (JSON + CSV)
```

## Related

- [Implementation plan](../implementation-plan.md)
- [Observability](../monitoring/observability.md)
