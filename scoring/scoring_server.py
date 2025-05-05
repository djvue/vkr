from fastapi import FastAPI
from pydantic import BaseModel
from scoring.scoring import setup_env, batch_get_rewards_async
import time


setup_env()

app = FastAPI()

sum_rt = 0.0
request_count = 0
sum_score = 0.0
score_count = 0

class EvaluateRequest(BaseModel):
    completions: list[str]
    project_path: list[str]
    relative_package_path: list[str]
    relative_file_path: list[str]


@app.get("/")
def read_root():
    return ''


@app.post("/score")
async def score(evaluate_request: EvaluateRequest):
    start = time.time()

    print(f"start request, len={len(evaluate_request.completions)}")

    scores = await batch_get_rewards_async(
        evaluate_request.completions,
        evaluate_request.project_path,
        evaluate_request.relative_package_path,
        evaluate_request.relative_file_path,
    )

    global sum_rt, request_count, sum_score, score_count
    sum_rt += time.time()-start
    request_count += 1
    sum_score += sum(scores)
    score_count += len(scores)
    print(f"ready request, len={len(evaluate_request.completions)}, scores={scores}, rt={time.time()-start}, avg_score={sum_score/score_count}, avg_rt={sum_rt/request_count}")

    return {"scores": scores}