import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import app


def test_agent_workflow_execution() -> None:
    """
    Integration test for Chronos Frame Agent workflow graph.
    Tests end-to-end node execution (NewsTool -> ImagenTool -> PublisherTool).
    """

    async def run_test():
        runner = InMemoryRunner(app=app)
        session = await runner.session_service.create_session(
            app_name="chronos_frame_agent", user_id="test_user"
        )

        events = []
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="Execute smart frame bulletin generation cycle"
                    )
                ],
            ),
        ):
            events.append(event)

        assert len(events) > 0, "Expected at least one workflow event"

        # Verify workflow output
        final_output = None
        for event in events:
            if event.output:
                final_output = event.output

        assert final_output is not None, "Workflow output was not returned"
        assert final_output.get("status") == "success"
        assert "smart_frame_web" in final_output.get("output_dir", "")
        assert len(final_output.get("fifo_queue", [])) <= 3

    asyncio.run(run_test())
