import asyncio
import RPi.GPIO as GPIO
import logging
import serial
import time
from typing import Optional

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


class PN532():
    def __init__(self,
                 port: str = '/dev/ttyS0',
                 baudrate: int = 115200,
                 reset: int = 20,
                 irq: Optional[int] = 16):

        self.reset = reset
        self.port = port
        self.baudrate = baudrate
        self._gpio_init(irq=irq, reset=self.reset)

    @classmethod
    async def ainit(cls) -> 'PN532':
        obj = PN532()
        for _ in range(4):
            obj.ser = serial.Serial(obj.port, obj.baudrate)
            if not obj.ser.is_open:
                msg = f"Cannot open port {obj.port}"
                logger.error(msg)
                raise RuntimeError(msg)

            await obj._reset(obj.reset)
            try:
                await obj._wakeup()
                await obj.get_firmware_version()  # first time often fails, try 2ce
                return obj
            except (ValueError, RuntimeError):
                continue
        msg = "Unable to connect to PN532"
        logger.error(msg)
        raise Exception(msg)

    def _gpio_init(self, irq: int = None, reset: int = None):
        self.irq = irq
        GPIO.setmode(GPIO.BCM)
        if reset:
            GPIO.setup(reset, GPIO.OUT)
            GPIO.output(reset, True)
        if irq:
            GPIO.setup(irq, GPIO.IN)

    async def _reset(self, pin: int):
        GPIO.output(pin, True)
        await asyncio.sleep(0.1)
        GPIO.output(pin, False)
        await asyncio.sleep(0.5)
        GPIO.output(pin, True)
        await asyncio.sleep(0.1)

    async def _write_data(self, framebytes):
        """Write a specified count of bytes to the PN532"""
        self.ser.read(self.ser.in_waiting)  # clear FIFO queue of UART
        self.ser.write(framebytes)

    async def _read_data(self, count):
        """Read a specified count of bytes from the PN532."""
        frame = self.ser.read(min(self.ser.in_waiting, count))
        if not frame:
            msg = "No data read from PN532"
            logger.error(msg)
            raise ValueError(msg)
        else:
            await asyncio.sleep(0.005)
        return frame

    async def _write_frame(self, data: bytes):
        # Build frame to send as:
        # - Preamble (0x00)
        # - Start code  (0x00, 0xFF)
        # - Command length (1 byte)
        # - Command length checksum
        # - Command bytes
        # - Checksum
        # - Postamble (0x00)
        length = len(data)
        frame = bytearray(length + 7)
        frame[0] = _PREAMBLE
        frame[1] = _STARTCODE1
        frame[2] = _STARTCODE2
        checksum = sum(frame[0:3])
        frame[3] = length & 0xFF
        frame[4] = (~length + 1) & 0xFF
        frame[5:-2] = data
        checksum += sum(data)
        frame[-2] = ~checksum & 0xFF
        frame[-1] = _POSTAMBLE
        await self._write_data(bytes(frame))

    async def _read_frame(self, length) -> Optional[bytes]:
        # Read frame with expected length of data.
        response = await self._read_data(length + 7)
        # Swallow all the 0x00 values that preceed 0xFF.
        offset = 0
        while response[offset] == 0x00:
            offset += 1
            if offset >= len(response):
                logger.error(
                    'Response frame preamble does not contain 0x00FF!')
                return None
        if response[offset] != 0xFF:
            logger.error('Response frame preamble does not contain 0x00FF!')
            return None

        offset += 1
        if offset >= len(response):
            logger.error('Response contains no data!')
            return None

        # Check length & length checksum match.
        frame_len = response[offset]
        if (frame_len + response[offset + 1]) & 0xFF != 0:
            logger.error('Response length checksum did not match length!')
            return None

        # Check frame checksum value matches bytes.
        checksum = sum(response[offset + 2:offset + 2 + frame_len + 1]) & 0xFF
        if checksum != 0:
            logger.error(
                'Response checksum did not match expected value: ', checksum)
            return None

        # Return frame data.
        return response[offset + 2:offset + 2 + frame_len]

    async def _wait_serial(self):
        while not self.ser.in_waiting:
            await asyncio.sleep(0.05)
        return True

    async def _wait_ready(self, timeout: float) -> bool:
        """Wait for response frame, up to `timeout` seconds"""
        try:
            await asyncio.wait_for(self._wait_serial(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def call_function(self,
                            command: bytes,
                            resp_len: int = 0,
                            params: bytes = bytes([]),
                            timeout: int = 1) -> Optional[bytes]:
        """
        Sends commands to device.
        A reponse of len `resp_len` is expected
        - params list of optional parameters
        """
        data = bytearray(2 + len(params))
        data[0] = _HOSTTOPN532
        data[1] = command & 0xFF
        for i, val in enumerate(params):
            data[2 + i] = val
        try:
            await self._write_frame(data)
        except OSError:
            await self._wakeup()
            return None

        if not await self._wait_ready(timeout):
            return None

        # Verify ACK response and wait to be ready for function response.
        if not _ACK == await self._read_data(len(_ACK)):
            # logger.error('Did not receive expected ACK from PN532!')
            return None
        if not await self._wait_ready(timeout):
            return None
        # Read response bytes.
        response = await self._read_frame(resp_len + 2)
        if response is None:
            return None
        # Check that response is for the called function.
        if not (response[0] == _PN532TOHOST and response[1] == (command + 1)):
            raise RuntimeError('Received unexpected command response!')
        # Return response data.
        return response[2:]

    async def get_firmware_version(self):
        """Call PN532 GetFirmwareVersion function and return a tuple with the IC,
        Ver, Rev, and Support values.
        """
        response = await self.call_function(
            _COMMAND_GETFIRMWAREVERSION, 4, timeout=0.5)

        if response is None:
            raise RuntimeError('Failed to detect the PN532')
        return tuple(response)

    async def SAM_configuration(self):   # pylint: disable=invalid-name
        """Configure the PN532 to read MiFare cards."""
        # Send SAM configuration command with configuration for:
        # - 0x01, normal mode
        # - 0x14, timeout 50ms * 20 = 1 second
        # - 0x01, use IRQ pin
        # Note that no other verification is necessary as call_function will
        # check the command was executed as expected.
        await self.call_function(_COMMAND_SAMCONFIGURATION,
                                 params=[0x01, 0x14, 0x01])

    async def _wakeup(self):
        self.ser.write(
            b'\x55\x55\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        await self.SAM_configuration()

    async def read_passive_target(self, card_baud=_MIFARE_ISO14443A, timeout=1) -> Optional[bytes]:
        """Wait for a MiFare card to be available and return its UID when found.
        Will wait up to timeout seconds and return None if no card is found,
        otherwise a bytearray with the UID of the found card is returned.
        """
        # Send passive read command for 1 card.  Expect at most a 7 byte UUID.
        response = await self.call_function(_COMMAND_INLISTPASSIVETARGET,
                                            params=[0x01, card_baud],
                                            resp_len=19,
                                            timeout=timeout)
        if response is None:
            return None
        # If no response is available return None to indicate no card is present.
        if response is None:
            return None
        # Check only 1 card with up to a 7 byte UID is present.
        if response[0] != 0x01:
            logger.error('More than one card detected!')
            return None
        if response[5] > 7:
            logger.error('Found card with unexpectedly long UID!')
            return None
        # Return UID of card.
        return response[6:6 + response[5]]
