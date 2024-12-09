import asyncio
import logging
from enum import IntEnum
from typing import Optional, Tuple, cast

from gpiozero import LED as Output
from gpiozero import Button as Input
from serial_asyncio import open_serial_connection
from systemd import journal

_HOSTTOPN532 = 0xD4
_PN532TOHOST = 0xD5
_PREAMBLE = 0x00
_STARTCODE1 = 0x00
_STARTCODE2 = 0xFF
_POSTAMBLE = 0x00
_ACK = b'\x00\x00\xFF\x00\xFF\x00'

_COMMAND_GETFIRMWAREVERSION = 0x02
_COMMAND_SAMCONFIGURATION = 0x14
_COMMAND_INLISTPASSIVETARGET = 0x4A

_MIFARE_ISO14443A = 0x00

logger = logging.getLogger('guguto-nfc')
logger.propagate = False
logger.addHandler(journal.JournaldLogHandler())
logger.setLevel(logging.WARNING)


class Status(IntEnum):
    OK = 0
    TIMEOUT = (1)
    CHECKSUM_ERROR = (1 << 1)
    MALFORMED = (1 << 2)
    ACK_ERROR = (1 << 3)
    CARD_ERROR = (1 << 4)


class PN532():
    def __init__(self,
                 port: str = '/dev/ttyAMA0',
                 baudrate: int = 115200,
                 reset: int = 20,
                 irq: Optional[int] = 16
                 ):

        self.port = port
        self.baudrate = baudrate
        self.reset = Output(reset)
        self.irq = Input(irq)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def ainit(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        await self._gpio_init()

        reader, writer = self.reader, self.writer
        if reader is None or writer is None:
            reader, writer = await open_serial_connection(url=self.port, baudrate=self.baudrate)
            self.reader, self.writer = reader, writer

        return cast(asyncio.StreamReader, reader), cast(asyncio.StreamWriter, writer)

    async def close(self) -> None:
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def _gpio_init(self):
        self.reset.on()

    async def _reset(self):
        self.reset.on()
        await asyncio.sleep(0.1)
        self.reset.off()
        await asyncio.sleep(0.5)
        self.reset.on()
        await asyncio.sleep(0.1)

    async def _write_data(self, framebytes: bytearray):
        """Write a specified count of bytes to the PN532"""
        _, writer = await self.ainit()
        writer.write(framebytes)
        await writer.drain()

    async def _read_data(self,
                         count: int,
                         read_exactly: bool = True,
                         timeout: float = 1) -> Tuple[int, bytearray]:
        """Read a specified count of bytes from the PN532."""
        reader, _ = await self.ainit()
        try:
            if read_exactly:
                data = await asyncio.wait_for(reader.readexactly(count), timeout)
            else:
                data = await asyncio.wait_for(reader.read(count), timeout)

        except asyncio.TimeoutError:
            return Status.TIMEOUT, bytearray([])
        return Status.OK, data

    async def _write_frame(self, data: bytearray):
        # Build frame to send as:
        # - Preamble (0x00)
        # - Start code  (0x00, 0xFF)
        # - Command length (1 byte)
        # - Command length checksum
        # - Command bytes
        # - Checksum
        # - Postamble (0x00)

        length = len(data)
        frame = bytearray([_PREAMBLE, _STARTCODE1, _STARTCODE2])
        checksum = sum(frame) + sum(data)
        frame += bytearray([length & 0xFF, (~length + 1) & 0xFF]) + data
        frame += bytearray([~checksum & 0xFF, _POSTAMBLE])

        await self._write_data(bytearray(frame))

    async def _read_frame(self,
                          length: int,
                          read_exactly: bool = True,
                          timeout: float = 1) -> Tuple[int, bytearray]:
        # Read frame with expected length of data.
        status, data = await self._read_data(length + 7, read_exactly=read_exactly, timeout=timeout)
        if status != Status.OK:
            return status, data

        if len(data) < 5:
            return Status.MALFORMED, data

        if data[:3] != bytearray([0, 0, 255]):
            logger.debug(
                'Response frame preamble does not contain 0x00FF!')
            return Status.MALFORMED, data

        # Check length & length checksum match.
        frame_len = data[3]
        if (frame_len + data[4]) & 0xFF != 0:
            logger.debug('Response length checksum did not match length!')
            return Status.MALFORMED, data

        # Check frame checksum value matches bytes.
        checksum = sum(data[5:5 + frame_len + 1]) & 0xFF
        if checksum != 0:
            logger.debug(
                'Response checksum did not match expected value: ', checksum)
            return Status.CHECKSUM_ERROR, data

        # Return frame data.
        return Status.OK, data[5:5 + 2 + frame_len]

    async def call_function(self,
                            command: int,
                            resp_len: int = 0,
                            params: bytearray = bytearray([]),
                            read_exactly: bool = True,
                            timeout: float = 1) -> Tuple[int, bytearray]:
        """
        Sends commands to device.
        A reponse of len `resp_len` is expected
        - params list of optional parameters
        """

        data = bytearray([_HOSTTOPN532, command & 0xFF]) + params
        await self._write_frame(data)

        # Verify ACK response and wait to be ready for function response.
        status, ack = await self._read_data(len(_ACK))
        if status != Status.OK:
            return status | Status.ACK_ERROR, ack

        status, data = await self._read_frame(resp_len + 2, timeout=timeout, read_exactly=read_exactly)

        if ack != _ACK:
            return status | Status.ACK_ERROR, data

        if status != Status.OK:
            return status, data

        if not (data[0] == _PN532TOHOST and data[1] == (command + 1)):
            logger.debug('Received unexpected command response!')
            return Status.MALFORMED, data

        return Status.OK, data[2:]

    async def get_firmware_version(self) -> Tuple[int, bytearray]:
        """Call PN532 GetFirmwareVersion function and return a tuple with the IC,
        Ver, Rev, and Support values.
        """
        return await self.call_function(_COMMAND_GETFIRMWAREVERSION, 4, timeout=0.5)

    async def SAM_configuration(self) -> Tuple[int, bytearray]:
        """Configure the PN532 to read MiFare cards."""
        # Send SAM configuration command with configuration for:
        # - 0x01, normal mode
        # - 0x14, timeout 50ms * 20 = 1 second
        # - 0x01, use IRQ pin
        return await self.call_function(_COMMAND_SAMCONFIGURATION,
                                        params=bytearray([0x01, 0x14, 0x01]))

    async def wakeup(self) -> Tuple[int, bytearray]:
        await self._write_data(
            bytearray(b'\x55\x55\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'))
        return await self.SAM_configuration()

    async def read_passive_target(self,
                                  card_baud=_MIFARE_ISO14443A,
                                  timeout: float = 1) -> Tuple[int, bytearray]:
        """Wait for a MiFare card to be available and return its UID when found.
        Will wait up to timeout seconds and return None if no card is found,
        otherwise a bytearray with the UID of the found card is returned.
        """
        # Send passive read command for 1 card.  Expect at most a 7 byte UUID.
        status, data = await self.call_function(_COMMAND_INLISTPASSIVETARGET,
                                                params=bytearray(
                                                    [0x01, card_baud]),
                                                resp_len=19,
                                                read_exactly=False,
                                                timeout=timeout)
        # If no response is available return None to indicate no card is present.
        if status != Status.OK:
            return status, data

        if data[0] != 0x01:
            logger.debug('More than one card detected!')
            return Status.CARD_ERROR, data
        if data[5] > 7:
            logger.debug('Found card with unexpectedly long UID!')
            return Status.CARD_ERROR, data

        # Return UID of card.
        return Status.OK, data[6:6 + data[5]]
