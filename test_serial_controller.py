"""Uji protokol serial dengan perangkat tiruan, tanpa Arduino fisik."""

from unittest.mock import patch

import serial_controller


class FakeSerial:
    def __init__(self, **_settings):
        self.is_open = True
        self.responses = [b"READY\n"]
        self.writes = []

    def reset_input_buffer(self):
        pass

    def readline(self):
        return self.responses.pop(0) if self.responses else b""

    def write(self, message):
        self.writes.append(message)
        self.responses.append(
            b"PONG\n" if message == b"PING\n" else b"DONE,2\n"
        )

    def flush(self):
        pass

    def close(self):
        self.is_open = False


def main():
    with patch.object(serial_controller.serial, "Serial", FakeSerial):
        serial_controller.connect("COM_TEST")
        assert serial_controller.is_connected()
        serial_controller.check_ready()
        serial_controller.dispense(2)
        assert serial_controller.serial_connection.writes == [
            b"PING\n",
            b"DISPENSE,2\n",
        ]
        serial_controller.disconnect()
        assert not serial_controller.is_connected()

    controller = FakeSerial()
    controller.responses = [b"READY\n", b"ERROR,INVALID_SLOT\n"]
    with patch.object(serial_controller.serial, "Serial", return_value=controller):
        serial_controller.connect("COM_TEST")
        try:
            serial_controller.dispense(2)
        except RuntimeError as exc:
            assert "INVALID_SLOT" in str(exc)
        else:
            raise AssertionError("Respons ERROR Arduino harus ditolak.")
        finally:
            serial_controller.disconnect()

    with (
        patch.object(serial_controller.serial, "Serial", FakeSerial),
        patch.object(serial_controller, "READY_TIMEOUT", 0),
    ):
        try:
            serial_controller.connect("COM_TEST")
        except TimeoutError:
            pass
        else:
            raise AssertionError("Koneksi tanpa READY harus timeout.")

    controller = FakeSerial()
    with (
        patch.object(serial_controller.serial, "Serial", return_value=controller),
        patch.object(serial_controller, "RESPONSE_TIMEOUT", 0),
    ):
        serial_controller.connect("COM_TEST")
        try:
            serial_controller.check_ready()
        except TimeoutError:
            assert not serial_controller.is_connected()
        else:
            raise AssertionError("Pemeriksaan tanpa PONG harus timeout.")

    import inventory
    assert [item['slot'] for item in inventory.create_product_list()] == [
        1, 2, 3, 4, 5, 6,
    ]

    with patch.object(
        inventory,
        "DEFAULT_PRODUCTS",
        [
            {'name': "Air", 'stock': 1, 'slot': 1},
            {'name': "Kopi", 'stock': 1, 'slot': 1},
        ],
    ):
        try:
            inventory.create_product_list()
        except ValueError as exc:
            assert "dipakai lebih dari sekali" in str(exc)
        else:
            raise AssertionError("Slot produk duplikat harus ditolak.")

    print("Semua uji serial lulus.")


if __name__ == "__main__":
    main()
