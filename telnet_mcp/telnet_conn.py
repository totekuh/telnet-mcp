import asyncio
import logging

import telnetlib3

logger = logging.getLogger(__name__)


class TelnetConnection:
    """Manages a persistent Telnet connection with lazy connect and auto-reconnect."""

    def __init__(self) -> None:
        self.host: str | None = None
        self.port: int | None = None
        self._reader: telnetlib3.TelnetReader | None = None
        self._writer: telnetlib3.TelnetWriter | None = None
        self._lock = asyncio.Lock()

    async def _connect(self) -> tuple[telnetlib3.TelnetReader, telnetlib3.TelnetWriter]:
        """Open a telnet connection. Raises on failure."""
        try:
            reader, writer = await telnetlib3.open_connection(
                host=self.host,
                port=self.port,
                connect_minwait=0.05,
            )
            logger.info("Connected to %s:%d", self.host, self.port)
            return reader, writer
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to {self.host}:{self.port} — {e}"
            ) from e

    def _is_connected(self) -> bool:
        """Check if the connection is still alive."""
        if self._reader is None or self._writer is None:
            return False
        if self._writer.transport is None or self._writer.transport.is_closing():
            return False
        return True

    async def connect(self, host: str, port: int) -> None:
        """Set target and open a connection."""
        async with self._lock:
            await self._close_unlocked()
            self.host = host
            self.port = port
            self._reader, self._writer = await self._connect()

    async def _ensure_connected(
        self,
    ) -> tuple[telnetlib3.TelnetReader, telnetlib3.TelnetWriter]:
        """Return an open connection, reconnecting if needed."""
        if self.host is None or self.port is None:
            raise ConnectionError(
                "Not connected. Use telnet_connect to connect to a host first."
            )
        if self._is_connected():
            return self._reader, self._writer  # type: ignore[return-value]
        await self._close_unlocked()
        self._reader, self._writer = await self._connect()
        return self._reader, self._writer

    async def _close_unlocked(self) -> None:
        """Close the connection without acquiring lock."""
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def _reconnect_once(
        self,
    ) -> tuple[telnetlib3.TelnetReader, telnetlib3.TelnetWriter]:
        """Close and reopen the connection. One attempt."""
        await self._close_unlocked()
        self._reader, self._writer = await self._connect()
        return self._reader, self._writer

    async def send_break(self) -> None:
        """Send Telnet BREAK signal (IAC BRK)."""
        async with self._lock:
            _, writer = await self._ensure_connected()
            writer.send_iac(b"\xff\xf3")  # IAC BRK

    async def disconnect(self) -> None:
        """Close the connection."""
        async with self._lock:
            await self._close_unlocked()
            logger.info("Disconnected from %s:%d", self.host, self.port)

    async def reconnect(self) -> None:
        """Force a fresh connection."""
        async with self._lock:
            await self._reconnect_once()

    async def write(self, data: str) -> None:
        """Send raw data to the telnet connection."""
        async with self._lock:
            _, writer = await self._ensure_connected()
            try:
                writer.write(data)
            except Exception:
                _, writer = await self._reconnect_once()
                writer.write(data)

    async def read(self, timeout: float = 1.0) -> str:
        """Read available data from telnet with timeout."""
        async with self._lock:
            return await self._read_unlocked(timeout)

    async def _read_unlocked(self, timeout: float) -> str:
        """Read from telnet without acquiring lock. Caller must hold lock."""
        reader, _ = await self._ensure_connected()
        buf: list[str] = []
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(
                    reader.read(4096), timeout=min(remaining, 0.2)
                )
                if chunk:
                    buf.append(chunk)
                else:
                    # EOF
                    break
            except asyncio.TimeoutError:
                if buf:
                    # Got data previously, nothing new — done
                    break
                continue
            except EOFError:
                break
        return "".join(buf)

    async def exec_command(self, command: str, timeout: float = 5.0) -> str:
        """Execute a command with __START__/__END__ markers and return clean output."""
        async with self._lock:
            reader, writer = await self._ensure_connected()

            # Drain any pending data
            try:
                await asyncio.wait_for(reader.read(65536), timeout=0.1)
            except (asyncio.TimeoutError, EOFError):
                pass

            wrapped = f"echo __START__; {command}; echo __END__\n"
            try:
                writer.write(wrapped)
            except Exception:
                reader, writer = await self._reconnect_once()
                writer.write(wrapped)

            buf: list[str] = []
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    chunk = await asyncio.wait_for(
                        reader.read(4096), timeout=min(remaining, 0.2)
                    )
                    if chunk:
                        buf.append(chunk)
                    else:
                        break
                except asyncio.TimeoutError:
                    pass
                except EOFError:
                    break

                text = "".join(buf)
                if "__END__" in text:
                    parsed = self._parse_markers(text)
                    if parsed is not None:
                        return parsed

            # Timeout — return what we have
            text = "".join(buf)
            parsed = self._parse_markers(text)
            if parsed is not None:
                return parsed
            return text.strip() + "\n[TIMEOUT]"

    @staticmethod
    def _parse_markers(text: str) -> str | None:
        """Extract output between __START__ and __END__ markers."""
        start_idx = text.find("__START__\n")
        if start_idx == -1:
            start_idx = text.find("__START__\r\n")
            if start_idx == -1:
                return None
            start_idx += len("__START__\r\n")
        else:
            start_idx += len("__START__\n")

        end_idx = text.find("__END__", start_idx)
        if end_idx == -1:
            return None

        return text[start_idx:end_idx].strip()

    def status(self) -> dict:
        """Return connection status."""
        return {
            "connected": self._is_connected(),
            "host": self.host,
            "port": self.port,
        }
