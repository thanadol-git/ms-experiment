import asyncio
import json
import uuid

import streamlit as st

from func.plate_plot import PLATE_CONFIGS

SERVER_URL = "https://hypha.aicell.io"

try:
    from hypha_rpc import connect_to_server
    from hypha_rpc.utils.schema import schema_function
except Exception:
    connect_to_server = None

    def schema_function(fn=None, **kwargs):
        if fn is None:
            return lambda f: f
        return fn


try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


def _safe_run(coro) -> None:
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def init_plate_replace_text(example_text: str) -> None:
    """Initialize the plate replacement text in session state."""
    if "pending_plate_update" in st.session_state:
        st.session_state.replace_pos_text = st.session_state.pending_plate_update
        del st.session_state.pending_plate_update
    if "replace_pos_text" not in st.session_state:
        st.session_state.replace_pos_text = example_text


@schema_function
def design_plate(plate_design_str: str) -> str:
    """Design a plate by setting the replacement positions text.

    The input string should be formatted as 'Label;Location' separated by newlines.
    Example: 'Pool;A7,A8,A12\\nControl;G12\\nEMPTY;A1\\nCohort_2;RowD\\nCohort_2;Col9'
    """
    plate_type = st.session_state.get("plate_type", "96-well")
    config = PLATE_CONFIGS[plate_type]
    rows = config["rows"]
    n_cols = config["n_cols"]
    valid_rows = "".join(rows)

    invalid = []
    for line in plate_design_str.strip().split("\n"):
        if ";" not in line:
            continue
        _, pos = line.split(";", 1)
        for p in [p.strip() for p in pos.split(",") if p.strip()]:
            if p.startswith("Row"):
                if not (len(p) == 4 and p[-1] in valid_rows):
                    invalid.append(p)
            elif p.startswith("Col"):
                if not (p[3:].isdigit() and 1 <= int(p[3:]) <= n_cols):
                    invalid.append(p)
            else:
                if not (len(p) >= 2 and p[0] in valid_rows and p[1:].isdigit() and 1 <= int(p[1:]) <= n_cols):
                    invalid.append(p)

    if invalid:
        return (
            f"Invalid positions for {plate_type}: {', '.join(invalid)}. "
            f"Valid rows: {rows[0]}–{rows[-1]}, columns: 1–{n_cols}. "
            "Please correct and try again."
        )

    st.session_state["pending_plate_update"] = plate_design_str
    return "Successfully updated plate design."


async def run_open_ai_agent(prompt: str, api_key: str) -> None:
    """Run the OpenAI agent with plate design tool."""
    if not AsyncOpenAI:
        st.error("OpenAI library not installed.")
        return

    plate_type = st.session_state.get("plate_type", "96-well")
    config = PLATE_CONFIGS[plate_type]
    rows = config["rows"]
    n_cols = config["n_cols"]

    client = AsyncOpenAI(api_key=api_key)
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "design_plate",
                "description": (
                    f"Design a {plate_type} plate (rows {rows[0]}–{rows[-1]}, columns 1–{n_cols}) "
                    "by setting the replacement positions text. "
                    f"Valid row shorthand: RowA–Row{rows[-1]}. "
                    f"Valid col shorthand: Col1–Col{n_cols}. "
                    "Comma-separated positions are allowed, e.g. 'Pool;A1,A3,A5'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plate_design_str": {
                            "type": "string",
                            "description": (
                                "Newline-separated entries formatted as 'Label;Position'. "
                                f"Rows: {rows[0]}–{rows[-1]}, Columns: 1–{n_cols}. "
                                "Supports single positions (A1), comma lists (A1,A3), "
                                f"row shorthand (RowA–Row{rows[-1]}), "
                                f"and col shorthand (Col1–Col{n_cols})."
                            ),
                        }
                    },
                    "required": ["plate_design_str"],
                },
            },
        }
    ]

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a helpful assistant that designs {plate_type} plates for mass spectrometry experiments.\n"
                f"Plate format: {plate_type} — rows {rows[0]} to {rows[-1]} ({len(rows)} rows), "
                f"columns 1 to {n_cols} ({n_cols} columns), total {len(rows) * n_cols} wells.\n"
                f"Position format: 'Label;Position' (e.g. Pool;A1 or Cohort_2;RowA or Control;Col{n_cols}).\n"
                f"The current plate design is:\n{st.session_state.replace_pos_text}"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=openai_tools, tool_choice="auto"
        )
    except Exception as e:
        st.error(f"OpenAI API Error: {e}")
        return

    message = completion.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            st.info(f"Agent calling tool: `{function_name}` with args: `{arguments}`")
            if function_name == "design_plate":
                st.success(design_plate(**arguments))
                st.rerun()
    else:
        st.write(message.content)


def create_agent_chat() -> None:
    """Render the AI agent chat interface for plate design."""
    api_key = st.text_input("OpenAI API Key", type="password")
    prompt = st.text_input("Prompt", "Set the plate to have Control at A1 and Pool at B2")

    if not st.button("Run Agent"):
        return

    if not api_key:
        st.warning("Please enter an OpenAI API Key.")
        return

    if connect_to_server is None:
        st.error(
            "Hypha RPC client is not available. Agent features are disabled. "
            "Install the optional dependency 'hypha-rpc' to enable this."
        )
        return

    async def start_and_chat():
        client_id = f"ms-experiment-{uuid.uuid4().hex[:8]}"
        st.session_state.service_id = client_id
        with st.spinner("Connecting to Hypha..."):
            async with connect_to_server({"server_url": SERVER_URL}) as server:
                await server.register_service({
                    "id": client_id,
                    "description": "Plate Design Service",
                    "config": {"visibility": "public"},
                    "design_plate": design_plate,
                })
                serve_task = asyncio.create_task(server.serve())
                await run_open_ai_agent(prompt, api_key)
                serve_task.cancel()
                try:
                    await serve_task
                except asyncio.CancelledError:
                    pass

    _safe_run(start_and_chat())
