import asyncio
import logging
from enum import IntEnum
from typing import Optional, Tuple, cast

from gpiozero import LED as Output
from gpiozero import Button as Input
from serial_asyncio import open_serial_connection

_HOSTTOPN532 = 0xD4
_PN532TOHOST = 0xD5
_PREAMBLE = 0x00
_STARTCODE1 = 0x00
_STARTCODE2 = 0xFF
_POSTAMBLE = 0x00
_ACK = b"\x00\x00\xff\x00\xff\x00"

_COMMAND_GETFIRMWAREVERSION = 0x02
_COMMAND_SAMCONFIGURATION = 0x14
_COMMAND_INLISTPASSIVETARGET = 0x4A

_MIFARE_ISO14443A = 0x00

logger = logging.getLogger("guguto-player")


class Status(IntEnum):
    OK = 0
    TIMEOUT = 1
    CHECKSUM_ERROR = 1 << 1
    MALFORMED = 1 << 2
    ACK_ERROR = 1 << 3
    CARD_ERROR = 1 << 4


class PN532:
    _ID = "32010607e800"

    def __init__(
        self,
        port: str = "/dev/ttyAMA0",
        baudrate: int = 115200,
        reset: int = 20,
        irq: int = 16,
    ):
        self.port = port
        self.baudrate = baudrate
        print(f"[DEBUG] Initializing PN532 on port={port}, baudrate={baudrate}")
        print(f"[DEBUG] Setting up reset GPIO pin {reset}")
        self.reset = Output(reset)
        print(f"[DEBUG] Setting up IRQ GPIO pin {irq} with pull_up=True")
        self.irq = Input(irq, pull_up=True)
        phys_state = "HIGH" if self.irq.value == 0 else "LOW"
        print(f"[DEBUG] IRQ pin initial state: is_active={self.irq.is_active}, value={self.irq.value} ({phys_state})")
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._irq_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._irq_enabled = False

    async def ainit(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        self._loop = asyncio.get_running_loop()

        self.irq.when_activated = self._irq_callback

        await self._gpio_init()

        reader, writer = self.reader, self.writer
        if reader is None or writer is None:
            print(f"[DEBUG] Opening serial connection to {self.port}")
            reader, writer = await open_serial_connection(
                url=self.port, baudrate=self.baudrate
            )
            self.reader, self.writer = reader, writer
            print("[DEBUG] Serial connection established")

        return cast(asyncio.StreamReader, reader), cast(asyncio.StreamWriter, writer)

    def _irq_callback(self):
        print(f"[DEBUG] IRQ callback fired! is_active={self.irq.is_active}, value={self.irq.value}")
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._irq_event.set)

    async def close(self) -> None:
        self.irq.when_activated = None
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def _gpio_init(self):
        self.reset.on()

    async def _reset(self):
        print("[DEBUG] Hardware reset: setting HIGH")
        self.reset.on()
        await asyncio.sleep(0.1)
        print("[DEBUG] Hardware reset: setting LOW")
        self.reset.off()
        await asyncio.sleep(0.5)
        print("[DEBUG] Hardware reset: setting HIGH again")
        self.reset.on()
        await asyncio.sleep(0.1)
        print("[DEBUG] Hardware reset complete")

    async def _write_data(self, framebytes: bytearray):
        """Write a specified count of bytes to the PN532"""
        _, writer = await self.ainit()
        print(f"[DEBUG] Writing {len(framebytes)} bytes: {framebytes.hex()}")
        writer.write(framebytes)
        await writer.drain()

    async def _wait_irq(self, timeout: float = 1.0) -> bool:
        """Wait for IRQ pin to become active (Low)."""
        phys_state = "HIGH" if self.irq.value == 0 else "LOW"
        print(f"[DEBUG] _wait_irq: checking pin state is_active={self.irq.is_active}, value={self.irq.value} ({phys_state})")
        if self.irq.is_active:
            print("[DEBUG] _wait_irq: pin already active")
            return True

        try:
            print(f"[DEBUG] _wait_irq: waiting for event (timeout={timeout}s)...")
            await asyncio.wait_for(self._irq_event.wait(), timeout)
            print("[DEBUG] _wait_irq: event fired!")
            return True
        except asyncio.TimeoutError:
            phys_state = "HIGH" if self.irq.value == 0 else "LOW"
            print(f"[DEBUG] _wait_irq: TIMEOUT - pin state is_active={self.irq.is_active}, value={self.irq.value} ({phys_state})")
            return False

    async def _read_data(
        self, count: int, read_exactly: bool = True, timeout: float = 1
    ) -> Tuple[int, bytearray]:
        """Read a specified count of bytes from the PN532."""
        reader, _ = await self.ainit()
        try:
            if read_exactly:
                data = await asyncio.wait_for(reader.readexactly(count), timeout)
            else:
                data = await asyncio.wait_for(reader.read(count), timeout)

        except asyncio.TimeoutError:
            print(f"[DEBUG] Read timeout after {timeout}s waiting for {count} bytes")
            return Status.TIMEOUT, bytearray([])
        except asyncio.IncompleteReadError as e:
            print(f"[DEBUG] Incomplete read: got {len(e.partial)} of {count} bytes")
            return Status.TIMEOUT, bytearray(e.partial) if e.partial else bytearray([])
        print(f"[DEBUG] Read {len(data)} bytes: {data.hex()}")
        return Status.OK, bytearray(data)

    def _build_frame(self, data: bytearray) -> bytearray:
        length = len(data)
        frame = bytearray([_PREAMBLE, _STARTCODE1, _STARTCODE2])
        checksum = sum(frame) + sum(data)
        frame += bytearray([length & 0xFF, (~length + 1) & 0xFF]) + data
        frame += bytearray([~checksum & 0xFF, _POSTAMBLE])
        return frame

    async def _write_frame(self, data: bytearray):
        frame = self._build_frame(data)
        await self._write_data(bytearray(frame))

    async def _read_frame(
        self, length: int, read_exactly: bool = True, timeout: float = 1
    ) -> Tuple[int, bytearray]:
        status, data = await self._read_data(
            length + 7, read_exactly=read_exactly, timeout=timeout
        )
        if status != Status.OK:
            return status, data

        if len(data) < 5:
            return Status.MALFORMED, data

        if data[:3] != bytearray([0, 0, 255]):
            logger.debug("Response frame preamble does not contain 0x00FF!")
            return Status.MALFORMED, data

        frame_len = data[3]
        if (frame_len + data[4]) & 0xFF != 0:
            logger.debug("Response length checksum did not match length!")
            return Status.MALFORMED, data

        checksum = sum(data[5 : 5 + frame_len + 1]) & 0xFF
        if checksum != 0:
            logger.debug("Response checksum did not match expected value: ", checksum)
            return Status.CHECKSUM_ERROR, data

        return Status.OK, data[5 : 5 + frame_len + 2]

    async def _flush_input(self):
        reader, _ = await self.ainit()
        flushed_bytes = 0
        try:
            while True:
                data = await asyncio.wait_for(reader.read(1024), timeout=0.01)
                if not data:
                    break
                flushed_bytes += len(data)
                print(f"[DEBUG] Flushed {len(data)} bytes: {data.hex()}")
        except asyncio.TimeoutError:
            pass
        if flushed_bytes > 0:
            print(f"[DEBUG] Total flushed: {flushed_bytes} bytes")

    async def call_function(
        self,
        command: int,
        resp_len: int = 0,
        params: bytearray = bytearray([]),
        read_exactly: bool = True,
        timeout: float = 1,
    ) -> Tuple[int, bytearray]:
        """
        Sends commands to device.
        A reponse of len `resp_len` is expected
        - params list of optional parameters
        """
        self._irq_event.clear()

        data = bytearray([_HOSTTOPN532, command & 0xFF]) + params
        print(f"[DEBUG] call_function: cmd=0x{command:02X}, params={len(params)}")
        await self._write_frame(data)

        if self._irq_enabled:
            if not await self._wait_irq(timeout=0.5):
                print("[DEBUG] Timeout waiting for IRQ (ACK) - falling back to serial read")
                # Fallthrough to read_data asynchronously as in nfc.py

        print(f"[DEBUG] Reading ACK ({len(_ACK)} bytes)...")
        status, ack = await self._read_data(len(_ACK))  # default 1s timeout
        if status != Status.OK:
            print(f"[DEBUG] Failed to read ACK: status={status}")
            return status | Status.ACK_ERROR, ack
        print(f"[DEBUG] Got ACK: {ack.hex()}")

        if self._irq_enabled:
            self._irq_event.clear()
            if not await self._wait_irq(timeout=timeout):
                print("[DEBUG] Timeout waiting for IRQ (response) - falling back to serial read")
                # Fallthrough to read_frame

        status, data = await self._read_frame(
            resp_len + 2, timeout=timeout, read_exactly=read_exactly
        )

        if ack != _ACK:
            print(f"[DEBUG] ACK mismatch: {ack.hex()}")
            return Status.ACK_ERROR, data

        print(f"[DEBUG] Response: status={status}, data={data.hex() if data else 'empty'}")

        if status != Status.OK:
            return status, data

        if len(data) < 2:
            print("[DEBUG] Response data too short")
            return Status.MALFORMED, data

        if not (data[0] == _PN532TOHOST and data[1] == (command + 1)):
            logger.debug(f"Unexpected response: got 0x{data[0]:02X} 0x{data[1]:02X}, expected 0x{_PN532TOHOST:02X} 0x{(command+1):02X}")
            return Status.MALFORMED, data

        return Status.OK, data[2:]

    async def get_firmware_version(self) -> Tuple[int, bytearray]:
        """Call PN532 GetFirmwareVersion function and return a tuple with the IC,
        Ver, Rev, and Support values.
        """
        return await self.call_function(_COMMAND_GETFIRMWAREVERSION, 4, timeout=0.5)

    async def SAM_configuration(self) -> Tuple[int, bytearray]:
        """Configure the PN532 to read MiFare cards."""
        print("[DEBUG] Calling SAM_configuration command...")
        status, data = await self.call_function(
            _COMMAND_SAMCONFIGURATION, params=bytearray([0x01, 0x14, 0x01])
        )
        print(f"[DEBUG] SAM_configuration result: status={status}, data={data.hex() if data else 'None'}")
        return status, data

    async def wakeup(self) -> Tuple[int, bytearray]:
        print("[DEBUG] Sending wakeup preamble (14 bytes like nfc.py)...")
        await self._write_data(
            bytearray([0x55, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        )
        print("[DEBUG] Wakeup sent, calling SAM_configuration...")
        return await self.SAM_configuration()

    async def read_passive_target(
        self, card_baud=_MIFARE_ISO14443A, timeout: float = 1
    ) -> Tuple[int, bytearray]:
        """Wait for a MiFare card to be available and return its UID when found.
        Will wait up to timeout seconds and return None if no card is found,
        otherwise a bytearray with the UID of the found card is returned.
        """
        status, data = await self.call_function(
            _COMMAND_INLISTPASSIVETARGET,
            params=bytearray([0x01, card_baud]),
            resp_len=19,
            read_exactly=False,
            timeout=timeout + 0.5,
        )
        if status != Status.OK:
            return status, data

        if data[0] != 0x01:
            logger.debug("More than one card detected!")
            return Status.CARD_ERROR, data
        if data[5] > 7:
            logger.debug("Found card with unexpectedly long UID!")
            return Status.CARD_ERROR, data
        # Return UID of card.
        return Status.OK, data[6 : 6 + data[5]]

    async def reset_device(self, ntries: int = 4, delay: float = 1) -> str:
        print(f"[DEBUG] reset_device called with ntries={ntries}")
        logger.info("Resetting PN532")
        for attempt in range(ntries):
            print(f"\n[DEBUG] ========== ATTEMPT {attempt + 1}/{ntries} ==========")
            self._irq_enabled = False
            self._irq_event.clear()

            await self._reset()

            try:
                print("[DEBUG] Calling wakeup()...")
                status, _ = await self.wakeup()
                if status != Status.OK:
                    print(f"[DEBUG] Wakeup/SAM config failed: status={status}")
                    logger.warning(f"Attempt {attempt + 1}: Wakeup/SAM config failed: {status}")
                    await asyncio.sleep(delay)
                    continue

                print("[DEBUG] Wakeup successful, getting firmware version...")
                status, response = await self.get_firmware_version()
                if status == Status.OK:
                    resp = response.hex()
                    print(f"[DEBUG] Firmware version: {resp}")
                    if resp == self._ID:
                        # Enable IRQ mode NOW after successful init
                        self._irq_enabled = True
                        print(f"[DEBUG] PN532 initialized successfully! IRQ mode enabled.")
                        logger.info(f"PN532 initialized successfully: {resp}")
                        return resp
                    else:
                        print(f"[DEBUG] Firmware ID mismatch: {resp} != {self._ID}")
                        logger.warning(f"Attempt {attempt + 1}: Firmware ID mismatch: {resp} != {self._ID}")
                else:
                    print(f"[DEBUG] GetFirmwareVersion failed: status={status}")
                    logger.warning(f"Attempt {attempt + 1}: GetFirmwareVersion failed: {status}")
            except Exception as e:
                print(f"[DEBUG] Exception during reset: {type(e).__name__}: {e}")
                logger.error(f"Attempt {attempt + 1}: Reset failed with exception: {e}")

            await asyncio.sleep(delay)

        raise RuntimeError("Unable to initialize PN532 device!")