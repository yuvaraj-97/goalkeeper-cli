import sys
import time
import subprocess
from goalkeeper_cli.core.event import GoalKeeperEvent
from goalkeeper_cli.core.dispatcher import dispatch_event

def run_command_wrapper(command_args: list[str]) -> None:
    if not command_args:
        print("❌ Error: No command provided to run.")
        print("Usage: goalkeeper run <command> [args...]")
        sys.exit(1)

    cmd_str = " ".join(command_args)
    source = command_args[0].capitalize()

    print(f"🥅 GoalKeeper: Wrapping execution for '{cmd_str}'...")

    # Emit session_start event
    start_event = GoalKeeperEvent(
        source=source,
        event_type="session_start",
        payload={"command": cmd_str}
    )
    dispatch_event(start_event)

    start_time = time.time()
    try:
        # Execute command, streaming outputs to terminal
        process = subprocess.Popen(
            command_args,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        exit_code = process.wait()
    except Exception as e:
        # Handle exceptions gracefully
        duration = time.time() - start_time
        fail_event = GoalKeeperEvent(
            source=source,
            event_type="task_failed",
            payload={
                "command": cmd_str,
                "error": str(e),
                "duration_seconds": duration
            }
        )
        dispatch_event(fail_event)
        print(f"\n🥅 GoalKeeper: Wrapped process failed to start: {e}")
        sys.exit(1)

    duration = time.time() - start_time
    payload = {
        "command": cmd_str,
        "exit_code": exit_code,
        "duration_seconds": duration
    }

    if exit_code == 0:
        event_type = "task_completed"
        # Since notify_on_completion might be false by default, we can force a completion alert
        # or rely on standard dispatch settings. Let's make wrapped run completions always notify
        # so wrapping non-hook tools (like aider) works out of the box!
        stop_event = GoalKeeperEvent(
            source=source,
            event_type=event_type,
            payload=payload
        )
        dispatch_event(stop_event)
        print(f"\n🥅 GoalKeeper: Wrapped process succeeded in {duration:.1f}s.")
    else:
        event_type = "task_failed"
        payload["stop_reason"] = f"Process exited with non-zero status code: {exit_code}"
        stop_event = GoalKeeperEvent(
            source=source,
            event_type=event_type,
            payload=payload
        )
        dispatch_event(stop_event)
        print(f"\n🥅 GoalKeeper: Wrapped process failed in {duration:.1f}s (exit code {exit_code}).")

    sys.exit(exit_code)
