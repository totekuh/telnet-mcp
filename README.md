# telnet-mcp

MCP server that gives [Claude Code](https://docs.anthropic.com/en/docs/claude-code) a shell on your device over Telnet. Send commands, read output, interact with remote consoles — directly from Claude.

## Install

```bash
pip install -e .
```

Requires Python 3.10+.

## Setup

```bash
claude mcp add --transport stdio --scope project telnet-mcp -- telnet-mcp
```

No environment variables needed — host and port are set dynamically via the `telnet_connect` tool.

## Tools

| Tool | Description |
|---|---|
| `telnet_connect(host, port=23)` | Connect to a Telnet host (must be called first) |
| `telnet_exec(command, timeout=5)` | Run a command, return clean output |
| `telnet_read(timeout=1)` | Read raw data from connection |
| `telnet_write(data)` | Send raw text (login, Ctrl-C `\x03`, etc.) |
| `telnet_interrupt()` | Send Ctrl-C to interrupt the running command |
| `telnet_send_break()` | Send Telnet BREAK signal (IAC BRK) |
| `telnet_disconnect()` | Close the connection |
| `telnet_reconnect()` | Force a fresh connection |
| `telnet_status()` | Check connection status |

## How It Works

- **On-demand connect** — call `telnet_connect` with host and port to establish a session
- **Persistent session** — connection stays open between calls
- **Auto-reconnect** — retries once if the connection drops
- **Async I/O** — uses telnetlib3 with asyncio
- **Marker parsing** — `telnet_exec` wraps commands with `echo __START__; <cmd>; echo __END__` for reliable output extraction

## License

MIT
