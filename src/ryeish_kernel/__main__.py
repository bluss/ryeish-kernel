import logging
import platform
import signal
import subprocess
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

RUN_CMD = ["rye", "run"]


def main():
    logging.basicConfig(level=logging.INFO)

    cmd = RUN_CMD + [
        "python", "-m", "ipykernel_launcher",
        *sys.argv[1:],
    ]
    proc = subprocess.Popen(cmd)

    if platform.system() == 'Windows':
        forward_signals = set(signal.Signals) - {signal.CTRL_BREAK_EVENT, signal.CTRL_C_EVENT, signal.SIGTERM}
    else:
        forward_signals = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}

    def handle_signal(sig, _frame):
        proc.send_signal(sig)

    for sig in forward_signals:
        signal.signal(sig, handle_signal)

    exit_code = proc.wait()
    if exit_code != 0:
        print("ipykernel_launcher exited with error code:", exit_code, file=sys.stderr)
        start_fallback_kernel()


def find_pyproject_file():
    cwd = Path().resolve()
    candidate_dirs = [cwd, *cwd.parents]
    for dirs in candidate_dirs:
        pyproject_file = dirs / "pyproject.toml"
        if pyproject_file.exists():
            return pyproject_file
    return None


def start_fallback_kernel():
    """
    Start a fallback kernel. Its purpose is

    1. Show a message that rye is not setup as expected in this environment
    2. Provide a regular ipython kernel which lets you run shell commands to fix rye!
    """
    has_pyproject = find_pyproject_file() is not None

    help_messages = []

    rye_init_messages = [
        "No pyproject.toml found - use rye init to start a new project?",
        "!rye init",
        "",
    ]

    if not has_pyproject:
        help_messages += rye_init_messages

    rye_kernel_messages = [
        "Failed to start Rye environment kernel - no ipykernel in rye project?",
        "Run these:",
        "!rye add ipykernel",
        "!rye sync",
        "",
        "Then restart the kernel to try again.",
    ]

    help_messages += rye_kernel_messages

    print("starting fallback kernel", file=sys.stderr)
    for msg in help_messages:
        print("ryeish-kernel:", msg, file=sys.stderr)

    import ipykernel.kernelapp
    import ipykernel.ipkernel
    from ipykernel.kernelapp import IPKernelApp

    class FallbackMessageKernel(ipykernel.ipkernel.IPythonKernel):
        def do_execute(self, *args, **kwargs):
            for msg in help_messages:
                print(msg, file=sys.stderr)
            return super().do_execute(*args, **kwargs)

    IPKernelApp.launch_instance(kernel_class=FallbackMessageKernel)


if __name__ == "__main__":
    main()
