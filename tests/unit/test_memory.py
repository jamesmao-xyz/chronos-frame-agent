from app.memory import HeadlineMemory, memory
from app.tools import news_tool


def test_headline_memory_deduplication():
    """Verify HeadlineMemory correctly detects duplicates and persists history."""
    test_memory = HeadlineMemory(filepath="smart_frame_web/.test_memory.json")
    test_memory.clear()

    # Add initial batch
    initial_batch = [
        "1. Global Technology Summit Unveils AI Silicon",
        "2. International Clean Energy Accord Expands Renewables",
    ]
    test_memory.add_headlines(initial_batch)

    # Verify duplicate detection
    assert (
        test_memory.is_duplicate("Global Technology Summit Unveils AI Silicon") is True
    )
    assert (
        test_memory.is_duplicate("Global Technology Summit Announces AI Silicon Chips")
        is True
    )
    assert test_memory.is_duplicate("James Webb Telescope Discovers Exoplanet") is False

    test_memory.clear()


def test_consecutive_news_tool_cycles_do_not_repeat():
    """Verify consecutive news_tool executions return distinct, non-repeating headlines."""
    memory.clear()

    # Cycle 1: Fetch 5 headlines
    cycle_1 = news_tool()
    assert cycle_1["status"] == "success"
    headlines_1 = set(cycle_1["headlines"])
    assert len(headlines_1) == 5

    # Cycle 2: Fetch next 5 headlines
    cycle_2 = news_tool()
    assert cycle_2["status"] == "success"
    headlines_2 = set(cycle_2["headlines"])
    assert len(headlines_2) == 5

    # Cycle 3: Fetch next 5 headlines
    cycle_3 = news_tool()
    assert cycle_3["status"] == "success"
    headlines_3 = set(cycle_3["headlines"])
    assert len(headlines_3) == 5

    # Verify that Cycle 1, Cycle 2, and Cycle 3 headlines have zero intersection
    assert (
        len(headlines_1.intersection(headlines_2)) == 0
    ), "Cycle 1 and Cycle 2 should not share duplicate headlines"
    assert (
        len(headlines_2.intersection(headlines_3)) == 0
    ), "Cycle 2 and Cycle 3 should not share duplicate headlines"
    assert (
        len(headlines_1.intersection(headlines_3)) == 0
    ), "Cycle 1 and Cycle 3 should not share duplicate headlines"
