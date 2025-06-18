#!/usr/bin/env python3
"""
CLI interface for the Agent.

This script provides a command-line interface for interacting with the Agent.
It instantiates an Agent and prompts the user for input, which is then passed to the Agent.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.panel import Panel

from prompts.instruction import INSTRUCTION_PROMPT
from tools.agent import Agent
from utils.llm_client import get_client
from utils.workspace_manager import WorkspaceManager

MAX_OUTPUT_TOKENS_PER_TURN = 32768
MAX_TURNS = 200


class JsonOutputHandler:
    """Handles JSON output formatting for structured communication."""

    def __init__(self, output_file=None):
        self.output_file = output_file

    def output_json_message(self, message_type: str, content: str, metadata: dict = None):
        """Output a structured JSON message."""
        message = {
            "type": message_type,
            "content": content,
            "timestamp": str(time.time()),
            "metadata": metadata or {}
        }
        json_str = json.dumps(message)
        print(json_str, flush=True)

        # Also write to file if specified
        if self.output_file:
            with open(self.output_file, 'a') as f:
                f.write(json_str + '\n')


def main():
    """Main entry point for the CLI."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CLI for interacting with the Agent")
    parser.add_argument(
        "--workspace",
        type=str,
        default=".",
        help="Path to the workspace",
    )
    parser.add_argument(
        "--problem-statement",
        type=str,
        default=None,
        help="Problem statement to pass to the agent. Makes the agent non-interactive.",
    )
    parser.add_argument(
        "--logs-path",
        type=str,
        default="agent_logs.txt",
        help="Path to save logs",
    )
    parser.add_argument(
        "--needs-permission",
        "-p",
        help="Ask for permission before executing commands",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--json-output",
        help="Output structured JSON messages instead of plain text",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--use-container-workspace",
        type=str,
        default=None,
        help="(Optional) Path to the container workspace to run commands in.",
    )
    parser.add_argument(
        "--docker-container-id",
        type=str,
        default=None,
        help="(Optional) Docker container ID to run commands in.",
    )
    parser.add_argument(
        "--minimize-stdout-logs",
        help="Minimize the amount of logs printed to stdout.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        default=None,
        choices=["anthropic", "openai"],
        help="LLM provider to use (default: anthropic, or from LLM_PROVIDER env var)",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model name (uses provider default if not specified, or from LLM_MODEL env var)",
    )
    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=None,
        help="Temperature for LLM generation (default: 0.0, or from LLM_TEMPERATURE env var)",
    )
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=None,
        help="Maximum tokens for LLM generation (default: 8192, or from LLM_MAX_TOKENS env var)",
    )

    args = parser.parse_args()

    # Initialize JSON output handler if needed
    json_handler = None

    if args.json_output:
        json_handler = JsonOutputHandler(args.logs_path if args.logs_path != "agent_logs.txt" else None)

    if os.path.exists(args.logs_path):
        os.remove(args.logs_path)
    logger_for_agent_logs = logging.getLogger("agent_logs")
    logger_for_agent_logs.setLevel(logging.DEBUG)
    logger_for_agent_logs.addHandler(logging.FileHandler(args.logs_path))
    if not args.minimize_stdout_logs and not args.json_output:
        logger_for_agent_logs.addHandler(logging.StreamHandler())
    else:
        logger_for_agent_logs.propagate = False

    # Determine LLM provider from CLI args or environment
    llm_provider = args.llm_provider or os.getenv("LLM_PROVIDER", "anthropic")

    # Check if required API key is set based on provider
    if llm_provider == "anthropic":
        if "ANTHROPIC_API_KEY" not in os.environ:
            print("Error: ANTHROPIC_API_KEY environment variable is not set.")
            print("Please set it to your Anthropic API key.")
            sys.exit(1)
    elif llm_provider == "openai":
        if "OPENAI_API_KEY" not in os.environ:
            print("Error: OPENAI_API_KEY environment variable is not set.")
            print("Please set it to your OpenAI API key.")
            sys.exit(1)
    else:
        print(f"Error: Unsupported LLM provider: {llm_provider}")
        print("Supported providers: anthropic, openai")
        sys.exit(1)

    # Initialize console
    console = Console()

    # Print welcome message (only if not in JSON mode)
    if not args.json_output and not args.minimize_stdout_logs:
        console.print(
            Panel(
                "[bold]Agent CLI[/bold]\n\n"
                + "Type your instructions to the agent. Press Ctrl+C to exit.\n"
                + "Type 'exit' or 'quit' to end the session.",
                title="[bold blue]Agent CLI[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
        )
    elif not args.json_output:
        logger_for_agent_logs.info(
            "Agent CLI started. Waiting for user input. Press Ctrl+C to exit. Type 'exit' or 'quit' to end the session."
        )

    # Get configuration from CLI args or environment variables
    llm_model = args.llm_model or os.getenv("LLM_MODEL")
    llm_temperature = args.llm_temperature if args.llm_temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.0"))
    llm_max_tokens = args.llm_max_tokens if args.llm_max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "8192"))

    # Set provider-specific defaults if model not specified
    if not llm_model:
        if llm_provider == "anthropic":
            llm_model = "claude-sonnet-4-20250514"  # Keep existing default
        elif llm_provider == "openai":
            llm_model = "gpt-4"

    # Build client configuration
    client_kwargs = {
        "model_name": llm_model,
        "temperature": llm_temperature,
        "max_tokens": llm_max_tokens,
    }

    # Add provider-specific parameters
    if llm_provider == "anthropic":
        client_kwargs.update({
            "use_caching": True,  # Keep existing default
            "thinking_tokens": 0,  # Keep existing default
        })
    elif llm_provider == "openai":
        client_kwargs.update({
            "cot_model": False,  # Keep existing default
        })

    # Initialize LLM client using existing get_client function
    client_name = f"{llm_provider}-direct"
    client = get_client(client_name, **client_kwargs)

    # Initialize workspace manager
    workspace_path = Path(args.workspace).resolve()
    workspace_manager = WorkspaceManager(
        root=workspace_path, container_workspace=args.use_container_workspace
    )

    # Initialize agent
    agent = Agent(
        client=client,
        workspace_manager=workspace_manager,
        console=console,
        logger_for_agent_logs=logger_for_agent_logs,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        ask_user_permission=args.needs_permission,
        docker_container_id=args.docker_container_id,
        json_handler=json_handler,
    )

    if args.problem_statement is not None:
        instruction = INSTRUCTION_PROMPT.format(
            location=(
                workspace_path
                if args.use_container_workspace is None
                else args.use_container_workspace
            ),
            pr_description=args.problem_statement,
        )
    else:
        instruction = None

    history = InMemoryHistory()
    # Send ready message in JSON mode
    if json_handler:
        json_handler.output_json_message(
            "system",
            "Agent CLI ready. Send messages to interact with the AI assistant.",
            {"workspace": workspace_path.as_posix(), "json_mode": True}
        )

    # Main interaction loop
    try:
        while True:
            # Get user input
            if instruction is None:
                if args.json_output:
                    # In JSON mode, read from stdin without prompt
                    try:
                        user_input = input()
                    except EOFError:
                        break
                else:
                    user_input = prompt("User input: ", history=history)
                    history.append_string(user_input)

                # Check for exit commands
                if user_input.lower() in ["exit", "quit"]:
                    if not args.json_output:
                        console.print("[bold]Exiting...[/bold]")
                    logger_for_agent_logs.info("Exiting...")
                    break
            else:
                user_input = instruction
                if not args.json_output:
                    logger_for_agent_logs.info(
                        f"User instruction:\n{user_input}\n-------------"
                    )

            # Run the agent with the user input
            if json_handler:
                json_handler.output_json_message("thinking", "Agent is thinking...")
                json_handler.output_json_message("user_input", user_input)
            else:
                logger_for_agent_logs.info("\nAgent is thinking...")

            try:
                result = agent.run_agent(user_input, resume=True)
                if json_handler:
                    json_handler.output_json_message("agent_response", result)
                else:
                    logger_for_agent_logs.info(f"Agent: {result}")
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                if json_handler:
                    json_handler.output_json_message("error", error_msg)
                else:
                    logger_for_agent_logs.info(error_msg)

            if not json_handler:
                logger_for_agent_logs.info("\n" + "-" * 40 + "\n")

            if instruction is not None:
                break

    except KeyboardInterrupt:
        if not args.json_output:
            console.print("\n[bold]Session interrupted. Exiting...[/bold]")

    if not args.json_output:
        console.print("[bold]Goodbye![/bold]")


if __name__ == "__main__":
    main()
