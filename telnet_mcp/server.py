import logging

from mcp.server.fastmcp import FastMCP

from telnet_mcp.telnet_conn import TelnetConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("telnet")
conn = TelnetConnection()


@mcp.tool()
async def telnet_connect(host: str, port: int = 23) -> str:
    """Connect to a Telnet host. Must be called before any other telnet tool."""
    try:
        await conn.connect(host, port)
        return f"[OK] Connected to {host}:{port}"
    except Exception as e:
        logger.exception("telnet_connect failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_exec(command: str, timeout: float = 5.0) -> str:
    """Execute a shell command on the Telnet-connected device and return its output.

    Wraps the command with markers for reliable output parsing.
    """
    try:
        return await conn.exec_command(command, timeout)
    except Exception as e:
        logger.exception("telnet_exec failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_read(timeout: float = 1.0) -> str:
    """Read raw data from the Telnet connection buffer.

    Useful for boot logs, long-running commands, or monitoring output.
    """
    try:
        data = await conn.read(timeout)
        return data if data else "[NO DATA]"
    except Exception as e:
        logger.exception("telnet_read failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_write(data: str) -> str:
    """Send raw data to the Telnet connection without waiting for a response.

    Useful for interactive prompts, login sequences, or sending control
    characters like Ctrl-C (\\x03).
    """
    try:
        await conn.write(data)
        return f"[OK] Sent {len(data)} bytes"
    except Exception as e:
        logger.exception("telnet_write failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_interrupt() -> str:
    """Send Ctrl-C to interrupt the currently running command on the device."""
    try:
        await conn.write("\x03")
        return "[OK] Sent Ctrl-C"
    except Exception as e:
        logger.exception("telnet_interrupt failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_send_break() -> str:
    """Send a Telnet BREAK signal (IAC BRK). Can drop to bootloader on some devices."""
    try:
        await conn.send_break()
        return "[OK] Sent BREAK"
    except Exception as e:
        logger.exception("telnet_send_break failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_disconnect() -> str:
    """Close the Telnet connection."""
    try:
        await conn.disconnect()
        return "[OK] Disconnected"
    except Exception as e:
        logger.exception("telnet_disconnect failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_reconnect() -> str:
    """Force a fresh Telnet connection (close existing and reconnect)."""
    try:
        await conn.reconnect()
        return "[OK] Reconnected"
    except Exception as e:
        logger.exception("telnet_reconnect failed")
        return f"[ERROR] {e}"


@mcp.tool()
async def telnet_status() -> dict:
    """Check the Telnet connection status."""
    return conn.status()


def main() -> None:
    mcp.run(transport="stdio")
