import json
import os
import queue
import subprocess
import threading
import time
from functools import wraps
from typing import Any, Dict, Optional

from models import BotState, ExecutionResult


def retry_on_broken_pipe(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to retry operations on broken pipe errors with exponential backoff."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except (BrokenPipeError, RuntimeError) as e:
                    last_exception = e
                    error_msg = str(e)

                    # Check if it's a broken pipe or process crash
                    if (
                        "broken pipe" in error_msg.lower()
                        or "process crashed" in error_msg.lower()
                    ):
                        if attempt < max_retries:
                            delay = base_delay * (2**attempt)  # Exponential backoff
                            print(
                                f"[RETRY] Attempt {attempt + 1}/{max_retries + 1} failed: {error_msg}"
                            )
                            print(
                                f"[RETRY] Restarting process and retrying in {delay:.1f}s..."
                            )

                            # Restart the process
                            self._restart_process()
                            time.sleep(delay)
                            continue
                        else:
                            print(f"[ERROR] All {max_retries + 1} attempts failed")
                            break
                    else:
                        # Re-raise if it's not a broken pipe error
                        raise
                except Exception:
                    # Re-raise non-broken-pipe exceptions immediately
                    raise

            # If we get here, all retries failed
            raise last_exception

        return wrapper

    return decorator


class MinecraftExecutor:
    """Python wrapper for Mineflayer bot with IPC communication."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.response_queue = queue.Queue()
        self.running = False
        self.reader_thread: Optional[threading.Thread] = None
        self.chat_log: list = []  # Store chat messages for context
        self.connection_config: Optional[Dict[str, Any]] = (
            None  # Store connection info for restart
        )

    def start(self):
        """Start the Node.js bot process."""
        # Use compiled JS from dist folder (TypeScript bot.ts is compiled to bot.js)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        bot_script = os.path.join(project_root, "dist", "minecraft", "bot.js")

        # Check if compiled file exists, if not provide helpful error
        if not os.path.exists(bot_script):
            raise FileNotFoundError(
                f"Compiled bot.js not found at {bot_script}. "
                "Please compile TypeScript files first by running: npm run build"
            )

        self.process = subprocess.Popen(
            ["node", bot_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
        )

        self.running = True
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

        # Wait for bot to be ready
        time.sleep(1)

    def _restart_process(self):
        """Restart the Node.js process and reconnect if needed."""
        print("[RESTART] Restarting bot process...")

        # Clean up existing process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                print(f"[RESTART] Error terminating old process: {e}")
            finally:
                self.process = None

        # Reset state
        self.running = False
        self.response_queue = queue.Queue()  # Clear the queue

        # Stop reader thread
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)

        # Start new process
        self.start()

        # Reconnect if we have connection config
        if self.connection_config:
            print("[RESTART] Reconnecting to Minecraft server...")
            try:
                self._send_message("connect", self.connection_config)
                self._wait_for_response("connected", timeout=30.0)
                print("[RESTART] Successfully reconnected")
            except Exception as e:
                print(f"[RESTART] Failed to reconnect: {e}")
                raise

    def _read_output(self):
        """Read output from Node.js process."""
        while self.running and self.process:
            line = self.process.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Check if it's a message from bot
            if line.startswith("MESSAGE:"):
                try:
                    message = json.loads(line[8:])
                    # Store chat messages for context
                    if message.get("type") == "chat":
                        self.chat_log.append(message["data"])
                        # Keep only last 20 chat messages
                        if len(self.chat_log) > 20:
                            self.chat_log = self.chat_log[-20:]
                    self.response_queue.put(message)
                except json.JSONDecodeError:
                    print(f"Failed to parse message: {line}")
            else:
                # Regular log output
                print(f"[Bot] {line}")

    def _send_message(self, msg_type: str, data: Any = None):
        """Send message to Node.js process."""
        if not self.process or not self.running:
            raise RuntimeError("Bot process not running")

        # Check if process is still alive before sending
        if self.process.poll() is not None:
            print(
                f"[ERROR] Process has terminated with exit code: {self.process.returncode}"
            )
            self.running = False
            raise RuntimeError("Bot process has terminated")

        try:
            message = json.dumps({"type": msg_type, "data": data})
            self.process.stdin.write(message + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            print("[ERROR] Broken pipe - Node.js process has crashed")
            print(
                f"[ERROR] Process exit code: {self.process.returncode if self.process else 'Unknown'}"
            )
            self.running = False
            raise RuntimeError("Bot process crashed (broken pipe)")
        except OSError as e:
            print(f"[ERROR] OS Error sending message: {e}")
            self.running = False
            raise RuntimeError(f"Bot process communication failed: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            raise

    def _wait_for_response(
        self, expected_type: str, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Wait for specific response type."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=1.0)
                if response["type"] == expected_type:
                    return response
                elif response["type"] == "error":
                    raise RuntimeError(f"Bot error: {response['data']}")
                else:
                    # Put it back if it's not what we're looking for
                    self.response_queue.put(response)
            except queue.Empty:
                continue

        raise TimeoutError(f"Timeout waiting for response type: {expected_type}")

    def connect(self, host: str = None, port: int = None, username: str = None):
        """Connect bot to Minecraft server."""
        config = {
            "host": host or self.config.get("host", "localhost"),
            "port": port or self.config.get("port", 25565),
            "username": username or self.config.get("username", "VoyagerBot"),
        }

        # Store connection config for potential restart
        self.connection_config = config

        self._send_message("connect", config)
        response = self._wait_for_response("connected", timeout=30.0)
        return response

    @retry_on_broken_pipe(max_retries=3, base_delay=1.0)
    def get_state(self) -> BotState:
        """Get current bot state."""
        self._send_message("get_state")
        response = self._wait_for_response("state", timeout=5.0)
        return BotState.from_dict(response["data"])

    def get_chat_log(self) -> list:
        """Get recent chat messages."""
        return self.chat_log.copy()

    def is_healthy(self) -> bool:
        """Check if the bot process is healthy and responsive."""
        if not self.process or not self.running:
            return False

        # Check if process is still alive
        if self.process.poll() is not None:
            print("[HEALTH] Process has terminated")
            return False

        # Try a simple ping to check responsiveness
        try:
            self._send_message("ping")
            self._wait_for_response("pong", timeout=2.0)
            return True
        except Exception as e:
            print(f"[HEALTH] Health check failed: {e}")
            return False

    @retry_on_broken_pipe(max_retries=3, base_delay=1.0)
    def execute_code(self, code: str, timeout: int = 60) -> ExecutionResult:
        """Execute JavaScript code in bot context."""

        self._send_message("execute", {"code": code, "timeout": timeout * 1000})

        response = self._wait_for_response("execution_result", timeout=timeout + 5)

        result_data = response["data"]
        return ExecutionResult(
            success=result_data.get("success", False),
            result=result_data.get("result"),
            error=result_data.get("error"),
            stack=result_data.get("stack"),
        )

    def disconnect(self):
        """Disconnect bot and cleanup."""
        if self.process and self.running:
            try:
                # Only try to send disconnect if process is still responsive
                if self.process.poll() is None:
                    self._send_message("disconnect")
                    self._wait_for_response("disconnected", timeout=5.0)
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.running = False
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                    except Exception as e:
                        print(f"Error terminating process: {e}")
                        # Force kill if terminate doesn't work
                        try:
                            self.process.kill()
                        except Exception:
                            pass
                    finally:
                        self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
