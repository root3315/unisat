"""BOM Generator — Generate Bill of Materials with component list."""

import csv
import io
from dataclasses import dataclass


@dataclass
class BOMItem:
    """Single BOM entry."""
    category: str
    component: str
    part_number: str
    quantity: int
    unit_price_usd: float
    supplier: str
    notes: str


DEFAULT_BOM = [
    BOMItem("OBC", "STM32F446RE Nucleo Board", "NUCLEO-F446RE", 1, 15.0, "ST", "Main MCU"),
    BOMItem("OBC", "SD Card Module", "MicroSD-SPI", 1, 3.0, "Generic", "Data storage"),
    BOMItem("EPS", "Solar Cell 40x80mm GaAs", "SC-3G30A", 6, 45.0, "SpectroLab", "Triple junction"),
    BOMItem("EPS", "18650 Li-ion Cell 3400mAh", "NCR18650B", 4, 8.0, "Panasonic", "Battery pack"),
    BOMItem("EPS", "MPPT Charge Controller", "SPV1040", 1, 5.0, "ST", "Solar charger"),
    BOMItem("COMM", "UHF Transceiver 437MHz", "CC1125", 1, 12.0, "TI", "AX.25 compatible"),
    BOMItem("COMM", "UHF Antenna (deployable)", "DPLA-437", 1, 25.0, "Custom", "Quarter-wave"),
    BOMItem("ADCS", "Magnetorquer Coil Set", "MTQ-3X", 3, 15.0, "Custom", "X/Y/Z axis"),
    BOMItem("ADCS", "Reaction Wheel Assembly", "RW-MICRO", 3, 120.0, "Custom", "Brushless motor"),
    BOMItem("ADCS", "Magnetometer LIS3MDL", "LIS3MDLTR", 1, 3.5, "ST", "3-axis"),
    BOMItem("ADCS", "IMU MPU-9250", "MPU-9250", 1, 8.0, "InvenSense", "9-DOF"),
    BOMItem("ADCS", "Sun Sensor Photodiode", "BPW34", 6, 1.5, "Osram", "Per face"),
    BOMItem("GNSS", "u-blox MAX-M10S", "MAX-M10S", 1, 15.0, "u-blox", "GNSS receiver"),
    BOMItem("GNSS", "Patch Antenna", "ANT-GPS", 1, 5.0, "Generic", "Ceramic"),
    BOMItem("Sensor", "BME280 Env Sensor", "BME280", 1, 4.0, "Bosch", "Temp/Press/Hum"),
    BOMItem("Sensor", "TMP117 Precision Temp", "TMP117", 2, 5.0, "TI", "±0.1°C"),
    BOMItem("Sensor", "Geiger Tube SBM-20", "SBM-20", 1, 20.0, "Centronic", "Radiation"),
    BOMItem("Sensor", "ADC MCP3008", "MCP3008-I/P", 1, 3.0, "Microchip", "8-ch 10-bit"),
    BOMItem("Camera", "Camera Module 8MP", "IMX219", 1, 25.0, "Sony", "CSI-2 interface"),
    BOMItem("Structure", "CubeSat Frame 3U", "CS-3U-AL", 1, 200.0, "Custom", "7075-T6 Al"),
    BOMItem("Structure", "PCB Stack Spacers", "M3-SPACER", 20, 0.5, "Generic", "Brass M3"),
    BOMItem("Thermal", "MLI Blanket", "MLI-10L", 1, 50.0, "Custom", "10-layer"),
    BOMItem("Harness", "Wire Harness Set", "AWG30-SET", 1, 30.0, "Custom", "Kapton insulated"),
]


def generate_bom(enabled_subsystems: dict[str, bool] | None = None) -> list[BOMItem]:
    """Generate BOM filtered by enabled subsystems."""
    if enabled_subsystems is None:
        return DEFAULT_BOM

    result = []
    always_include = {"OBC", "Structure", "Thermal", "Harness"}

    cat_map = {
        "EPS": "eps", "COMM": "comm", "ADCS": "adcs",
        "GNSS": "gnss", "Camera": "camera", "Sensor": "payload",
    }

    for item in DEFAULT_BOM:
        if item.category in always_include:
            result.append(item)
        elif item.category in cat_map:
            subsys = cat_map[item.category]
            if enabled_subsystems.get(subsys, False):
                result.append(item)

    return result


def bom_to_csv(bom: list[BOMItem]) -> str:
    """Convert BOM to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Component", "Part Number", "Qty",
                     "Unit Price (USD)", "Total (USD)", "Supplier", "Notes"])

    total_cost = 0.0
    for item in bom:
        line_total = item.quantity * item.unit_price_usd
        total_cost += line_total
        writer.writerow([
            item.category, item.component, item.part_number,
            item.quantity, f"${item.unit_price_usd:.2f}",
            f"${line_total:.2f}", item.supplier, item.notes,
        ])

    writer.writerow([])
    writer.writerow(["", "", "", "", "TOTAL:", f"${total_cost:.2f}", "", ""])

    return output.getvalue()
