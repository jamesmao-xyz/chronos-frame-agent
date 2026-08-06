import asyncio
import json
import os
from datetime import datetime

from google.adk.runners import InMemoryRunner
from google.genai import types
from PIL import Image

from app.agent import app

EVAL_DATASET = os.path.join(
    os.path.dirname(__file__), "datasets", "chronos_eval_dataset.json"
)
RESULTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "grade_results")
)


async def run_evaluation():
    """Runs the Chronos Frame Agent evaluation suite over chronos_eval_dataset.json."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(EVAL_DATASET, encoding="utf-8") as f:
        data = json.load(f)

    eval_cases = data.get("eval_cases", [])
    results = []

    runner = InMemoryRunner(app=app)

    print(f"=== Starting ADK 2 Evaluation ({len(eval_cases)} cases) ===")

    passed_count = 0

    for case in eval_cases:
        case_id = case.get("eval_case_id")
        user_prompt = case.get("prompt", {}).get("parts", [{}])[0].get("text", "")

        session = await runner.session_service.create_session(
            app_name="chronos_frame_agent", user_id="eval_user"
        )

        events = []
        async for event in runner.run_async(
            user_id="eval_user",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=user_prompt)]
            ),
        ):
            events.append(event)

        final_output = None
        for event in events:
            if event.output:
                final_output = event.output

        # Metric 1: Workflow Success
        is_success = (
            final_output is not None and final_output.get("status") == "success"
        )

        # Metric 2: Image Dimensions (1080x1920)
        img_path = os.path.abspath("smart_frame_web/image_1.png")
        dim_pass = False
        if os.path.exists(img_path):
            with Image.open(img_path) as img:
                dim_pass = img.size == (1080, 1920)

        # Metric 3: FIFO Queue limit (<= 3)
        fifo_pass = (
            final_output is not None and len(final_output.get("fifo_queue", [])) <= 3
        )

        case_passed = is_success and dim_pass and fifo_pass
        if case_passed:
            passed_count += 1

        results.append(
            {
                "eval_case_id": case_id,
                "prompt": user_prompt,
                "passed": case_passed,
                "metrics": {
                    "chronos_workflow_quality": 1.0 if is_success else 0.0,
                    "image_dimension_metric": 1.0 if dim_pass else 0.0,
                    "fifo_queue_compliance": 1.0 if fifo_pass else 0.0,
                },
            }
        )

        status_str = "PASS" if case_passed else "FAIL"
        print(
            f"[{status_str}] {case_id}: workflow={is_success}, dims_1080x1920={dim_pass}, fifo<=3={fifo_pass}"
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(RESULTS_DIR, f"results_{ts}.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_cases": len(eval_cases),
                "passed_cases": passed_count,
                "pass_rate": passed_count / len(eval_cases) if eval_cases else 0.0,
                "cases": results,
            },
            f,
            indent=2,
        )

    print(
        f"\nEvaluation Complete! Pass Rate: {passed_count}/{len(eval_cases)} ({passed_count / len(eval_cases) * 100:.1f}%)"
    )
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
