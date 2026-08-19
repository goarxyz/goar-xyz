from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from pydantic import ValidationError
from rich import print as rprint

from vibe import __version__
from vibe.cli.session_exit import print_session_resume_message
from vibe.cli.terminal_detect import detect_terminal
from vibe.core.config import MissingAPIKeyError, VibeConfigSchema, load_dotenv_values
from vibe.core.config.default_orchestrator import build_default_orchestrator
from vibe.core.config.orchestrator import ConfigOrchestrator
from vibe.core.paths import HISTORY_FILE
from vibe.core.telemetry.build_metadata import build_launch_context
from vibe.core.telemetry.types import LaunchContext
from vibe.observability.logging import logger

# The TUI app, onboarding, update prompt, and programmatic runner are each
# imported at their call site: every launch needs at most one of them, and
# they are too heavy to load speculatively at startup.

if TYPE_CHECKING:
    from vibe.app_server.local import LocalSessionIntent
    from vibe.setup.update_prompt import UpdatePromptMode


def _build_cli_launch_context() -> LaunchContext:
    return build_launch_context(
        agent_entrypoint="cli",
        agent_version=__version__,
        client_name="vibe_cli",
        client_version=__version__,
        terminal_emulator=detect_terminal(),
    )


def get_prompt_from_stdin() -> str | None:
    if sys.stdin.isatty():
        return None
    try:
        content = sys.stdin.read().strip()
    except KeyboardInterrupt:
        return None
    if content:
        try:
            sys.stdin = sys.__stdin__ = open("/dev/tty")
        except OSError:
            pass
        return content
    return None


def _format_config_validation_error(exc: ValidationError) -> str:
    lines = [f"Invalid configuration ({exc.error_count()} error(s)):"]
    for err in exc.errors(include_url=False):
        loc = ".".join(str(part) for part in err["loc"]) or "<root>"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)


def load_config_orchestrator_or_exit(
    *, interactive: bool
) -> ConfigOrchestrator[VibeConfigSchema]:
    try:
        return asyncio.run(build_default_orchestrator())
    except MissingAPIKeyError as e:
        if not interactive:
            print(
                f"Error: {e}. Set the environment variable (e.g. in ~/.vibe/.env "
                "or your shell), or run `vibe --setup` once interactively.",
                file=sys.stderr,
            )
            sys.exit(1)

        from vibe.setup.onboarding import run_onboarding

        return run_onboarding(launch_context=_build_cli_launch_context())
    except ValidationError as e:
        rprint(f"[yellow]{_format_config_validation_error(e)}[/]")
        sys.exit(1)
    except ValueError as e:
        rprint(f"[yellow]{e}[/]")
        sys.exit(1)


def bootstrap_config_files() -> None:
    history_file = HISTORY_FILE.path
    if not history_file.exists():
        try:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            history_file.write_text("Hello Vibe!\n", "utf-8")
        except Exception as e:
            rprint(f"[yellow]Could not create history file: {e}[/]")


def _session_intent(
    args: argparse.Namespace, *, allow_picker: bool
) -> LocalSessionIntent:
    from vibe.app_server.local import (
        ContinueSessionIntent,
        NewSessionIntent,
        ResumeSessionIntent,
    )

    if args.continue_session:
        return ContinueSessionIntent()
    if args.resume is True:
        if allow_picker:
            return NewSessionIntent()
        raise ValueError("--resume requires a session ID in programmatic mode")
    if isinstance(args.resume, str):
        return ResumeSessionIntent(args.resume)
    return NewSessionIntent()


def _run_programmatic_mode(args: argparse.Namespace, stdin_prompt: str | None) -> None:
    from vibe.app_server.local import ClientDescriptor, LocalHarnessOptions
    from vibe.app_server.protocol import (
        AppServerResponseError,
        ClientCapabilities,
        ClientInfo,
        SessionOptions,
    )
    from vibe.cli.programmatic import (
        OutputFormat,
        ProgrammaticLimitError,
        ProgrammaticTeleportError,
        run_programmatic,
    )

    programmatic_prompt = args.prompt or stdin_prompt
    if not programmatic_prompt:
        print("Error: No prompt provided for programmatic mode", file=sys.stderr)
        sys.exit(1)
    output_format = OutputFormat(args.output if hasattr(args, "output") else "text")

    try:
        session_intent = _session_intent(args, allow_picker=False)
        final_response = run_programmatic(
            harness_options=LocalHarnessOptions(
                experimental_harness=args.experimental_harness,
                client=ClientDescriptor(
                    info=ClientInfo(
                        name="vibe_programmatic",
                        title="Vibe programmatic CLI",
                        version=__version__,
                        entrypoint="programmatic",
                        terminal_emulator=detect_terminal(),
                    ),
                    capabilities=ClientCapabilities(
                        callback_kinds=["approval", "user_input"]
                    ),
                ),
                session_options=SessionOptions(
                    cwd=str(Path.cwd()),
                    workspace_roots=list(args.add_dir),
                    agent=args.agent,
                    auto_approve=args.auto_approve,
                    enabled_tools=args.enabled_tools,
                    disabled_tools=[
                        *(args.disabled_tools or ()),
                        "ask_user_question",
                        "exit_plan_mode",
                    ],
                    max_turns=args.max_turns,
                    max_price=args.max_price,
                    max_session_tokens=args.max_tokens,
                    headless=True,
                    trust_workspace=bool(args.trust or args.worktree),
                ),
                session=session_intent,
            ),
            prompt=programmatic_prompt or "",
            output_format=output_format,
            teleport=args.teleport,
        )
        if final_response:
            print(final_response)
        sys.exit(0)
    except ProgrammaticLimitError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except ProgrammaticTeleportError as e:
        print(f"Teleport error: {e}", file=sys.stderr)
        sys.exit(1)
    except AppServerResponseError as e:
        print(f"Error: {e.error.message}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _run_interactive_mode(
    args: argparse.Namespace,
    stdin_prompt: str | None,
) -> None:
    from vibe.app_server.local import (
        ClientDescriptor,
        LocalHarness,
        LocalHarnessOptions,
    )
    from vibe.app_server.protocol import (
        AppServerResponseError,
        ClientCapabilities,
        ClientInfo,
        SessionOptions,
    )
    from vibe.cli.textual_ui.app import StartupOptions, run_textual_ui

    harness = LocalHarness(
        LocalHarnessOptions(
            experimental_harness=args.experimental_harness,
            client=ClientDescriptor(
                info=ClientInfo(
                    name="vibe_tui",
                    title="Vibe Textual",
                    version=__version__,
                    entrypoint="cli",
                    terminal_emulator=detect_terminal(),
                ),
                capabilities=ClientCapabilities(
                    callback_kinds=["approval", "user_input"]
                ),
            ),
            session_options=SessionOptions(
                cwd=str(Path.cwd()),
                workspace_roots=list(args.add_dir),
                agent=args.agent,
                auto_approve=args.auto_approve,
                enabled_tools=args.enabled_tools,
                disabled_tools=list(args.disabled_tools or ()),
                trust_workspace=bool(args.trust or args.worktree),
            ),
            session=_session_intent(args, allow_picker=True),
        )
    )
    try:
        summary = run_textual_ui(
            start_app_server=harness.connect,
            history_file=HISTORY_FILE.path,
            update_cache_repository=None,
            startup=StartupOptions(
                initial_prompt=args.initial_prompt or stdin_prompt,
                teleport_on_start=args.teleport,
                show_resume_picker=args.resume is True,
                is_resuming_session=(
                    args.continue_session or isinstance(args.resume, str)
                ),
                prompt_for_workspace_trust=True,
                resume_session_id=(
                    args.resume if isinstance(args.resume, str) else None
                ),
                continue_latest=bool(args.continue_session),
            ),
        )
    except AppServerResponseError as exc:
        rprint(f"[red]Error:[/] {exc.error.message}")
        sys.exit(1)
    print_session_resume_message(summary)


def run_cli(args: argparse.Namespace) -> None:
    """Run the full Mistral Vibe CLI without update or crash-reporting services."""
    load_dotenv_values()
    bootstrap_config_files()

    if args.setup:
        from vibe.setup.onboarding import run_onboarding

        run_onboarding(launch_context=_build_cli_launch_context())
        sys.exit(0)

    if getattr(args, "check_upgrade", False):
        rprint(
            f"[dim]Alpine Private Vibe {__version__}: update checks and automatic updates are disabled.[/]"
        )
        sys.exit(0)

    try:
        is_interactive = args.prompt is None
        load_config_orchestrator_or_exit(interactive=is_interactive)
        stdin_prompt = get_prompt_from_stdin()
        if is_interactive:
            _run_interactive_mode(args=args, stdin_prompt=stdin_prompt)
        else:
            _run_programmatic_mode(args=args, stdin_prompt=stdin_prompt)
    except (KeyboardInterrupt, EOFError):
        rprint("\n[dim]Bye![/]")
        sys.exit(0)
