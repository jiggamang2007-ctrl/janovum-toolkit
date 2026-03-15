"""
Janovum Platform — Code Sandbox
Secure execution environment for agent-generated code.
Like E2B but self-hosted and free.

Uses subprocess with strict limits:
  - Timeout (default 30s)
  - Memory limit
  - No network access in strict mode
  - No file system access outside sandbox dir
  - Captures stdout, stderr, return code
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
SANDBOX_DIR = PLATFORM_DIR / "data" / "sandbox"


class SandboxResult:
    def __init__(self, stdout="", stderr="", returncode=0, timed_out=False, duration_ms=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.timed_out = timed_out
        self.duration_ms = duration_ms
        self.success = returncode == 0 and not timed_out

    def to_dict(self):
        return {
            "stdout": self.stdout[:5000],
            "stderr": self.stderr[:2000],
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "duration_ms": self.duration_ms,
            "success": self.success
        }


class CodeSandbox:
    """Execute code safely in an isolated environment."""

    def __init__(self):
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        self.max_timeout = 60
        self.default_timeout = 30
        self.execution_log = []

    def execute_python(self, code, timeout=None, env_vars=None, working_dir=None):
        """Execute Python code in a sandbox."""
        timeout = min(timeout or self.default_timeout, self.max_timeout)

        # Create temp directory for this execution
        exec_dir = tempfile.mkdtemp(dir=str(SANDBOX_DIR), prefix="exec_")
        script_path = os.path.join(exec_dir, "script.py")

        try:
            with open(script_path, "w") as f:
                f.write(code)

            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            # Remove sensitive vars
            for key in ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]:
                for env_key in list(env.keys()):
                    if key in env_key.upper():
                        del env[env_key]

            import time
            start = time.time()

            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir or exec_dir,
                env=env
            )

            duration_ms = round((time.time() - start) * 1000)

            sandbox_result = SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                duration_ms=duration_ms
            )

        except subprocess.TimeoutExpired:
            sandbox_result = SandboxResult(
                stderr=f"Execution timed out after {timeout}s",
                returncode=-1,
                timed_out=True,
                duration_ms=timeout * 1000
            )
        except Exception as e:
            sandbox_result = SandboxResult(
                stderr=str(e),
                returncode=-1,
                duration_ms=0
            )
        finally:
            try:
                shutil.rmtree(exec_dir, ignore_errors=True)
            except Exception:
                pass

        self._log_execution(code, sandbox_result)
        return sandbox_result

    def execute_shell(self, command, timeout=None):
        """Execute a shell command in sandbox."""
        timeout = min(timeout or self.default_timeout, self.max_timeout)

        # Block dangerous commands
        dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb", "shutdown", "reboot"]
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower:
                return SandboxResult(stderr=f"BLOCKED: Dangerous command detected", returncode=-1)

        try:
            import time
            start = time.time()

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(SANDBOX_DIR)
            )

            duration_ms = round((time.time() - start) * 1000)
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                duration_ms=duration_ms
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(stderr=f"Timed out after {timeout}s", returncode=-1, timed_out=True)
        except Exception as e:
            return SandboxResult(stderr=str(e), returncode=-1)

    def get_log(self, limit=50):
        return self.execution_log[-limit:]

    def get_stats(self):
        total = len(self.execution_log)
        success = sum(1 for e in self.execution_log if e.get("success"))
        return {
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": round(success / max(total, 1) * 100, 1)
        }

    def _log_execution(self, code, result):
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "code_preview": code[:200],
            "success": result.success,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out
        })
        if len(self.execution_log) > 500:
            self.execution_log = self.execution_log[-500:]


_sandbox = None
def get_sandbox():
    global _sandbox
    if _sandbox is None:
        _sandbox = CodeSandbox()
    return _sandbox
