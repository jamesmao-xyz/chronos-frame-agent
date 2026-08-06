# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Any

from google.adk.apps import App
from google.adk.workflow import START, Workflow

from app.tools import imagen_tool, news_tool, publisher_tool

logger = logging.getLogger(__name__)


# Node 1: News fetching and safety summarization
def news_node(node_input: Any = None) -> dict[str, Any]:
    """Graph Node 1: Ingest top 3 global news items and summarize."""
    logger.info("Executing Graph Node 1: NewsTool")
    result = news_tool()
    return result


# Node 2: Portrait bulletin image rendering
def imagen_node(node_input: dict[str, Any]) -> dict[str, Any]:
    """Graph Node 2: Generate 1080x1920 9:16 portrait bulletin image."""
    logger.info("Executing Graph Node 2: ImagenTool")
    summary = node_input.get("summary", "")
    timestamp = node_input.get("timestamp", "")
    image_result = imagen_tool(headline_summary=summary, timestamp=timestamp)
    return image_result


# Node 3: 3-Image FIFO queue management and local web publishing
def publisher_node(node_input: dict[str, Any]) -> dict[str, Any]:
    """Graph Node 3: Enforce 3-image FIFO queue in smart_frame_web/ directory."""
    logger.info("Executing Graph Node 3: PublisherTool")
    pub_result = publisher_tool(image_data=node_input)
    return pub_result


# Construct ADK 2.0 Graph Workflow Agent
root_agent = Workflow(
    name="chronos_frame_agent",
    description="Autonomous ADK 2.0 graph workflow agent that ingests news, generates 9:16 bulletin graphics, and publishes to a 3-image FIFO smart frame web server.",
    edges=[
        (START, news_node),
        (news_node, imagen_node),
        (imagen_node, publisher_node),
    ],
)

app = App(
    root_agent=root_agent,
    name="chronos_frame_agent",
)
