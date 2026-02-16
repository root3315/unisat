"""Link Budget Calculator — SNR and BER for UHF and S-band."""

import math
from dataclasses import dataclass

BOLTZMANN = 1.380649e-23  # J/K
SPEED_OF_LIGHT = 299792458  # m/s


@dataclass
class LinkBudget:
    """Link budget calculation results."""
    frequency_mhz: float
    tx_power_dbm: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    distance_km: float
    free_space_loss_db: float
    atmospheric_loss_db: float
    received_power_dbm: float
    noise_floor_dbm: float
    snr_db: float
    margin_db: float
    max_data_rate_bps: float
    ber: float


def calculate_link_budget(
    frequency_mhz: float, tx_power_w: float, tx_gain_dbi: float,
    rx_gain_dbi: float, distance_km: float, data_rate_bps: float,
    system_noise_temp_k: float = 500.0, atmospheric_loss_db: float = 1.0,
    implementation_loss_db: float = 2.0, required_ebno_db: float = 10.0,
) -> LinkBudget:
    """Calculate complete link budget."""
    freq_hz = frequency_mhz * 1e6
    dist_m = distance_km * 1e3

    tx_power_dbm = 10 * math.log10(tx_power_w * 1000)

    # Free space path loss
    fspl = 20 * math.log10(dist_m) + 20 * math.log10(freq_hz) + \
           20 * math.log10(4 * math.pi / SPEED_OF_LIGHT)

    # EIRP
    eirp_dbm = tx_power_dbm + tx_gain_dbi

    # Received power
    rx_power_dbm = eirp_dbm - fspl + rx_gain_dbi - atmospheric_loss_db - implementation_loss_db

    # Noise floor
    bandwidth_hz = data_rate_bps * 1.2  # Approximate
    noise_power = BOLTZMANN * system_noise_temp_k * bandwidth_hz
    noise_dbm = 10 * math.log10(noise_power * 1000)

    # SNR
    snr_db = rx_power_dbm - noise_dbm

    # Eb/No
    ebno = snr_db - 10 * math.log10(data_rate_bps / bandwidth_hz)

    # Margin
    margin = ebno - required_ebno_db

    # BER estimation (BPSK approximation)
    ebno_linear = 10 ** (ebno / 10)
    ber = 0.5 * math.erfc(math.sqrt(ebno_linear))

    # Shannon capacity
    snr_linear = 10 ** (snr_db / 10)
    max_rate = bandwidth_hz * math.log2(1 + snr_linear)

    return LinkBudget(
        frequency_mhz=frequency_mhz, tx_power_dbm=tx_power_dbm,
        tx_gain_dbi=tx_gain_dbi, rx_gain_dbi=rx_gain_dbi,
        distance_km=distance_km, free_space_loss_db=round(fspl, 1),
        atmospheric_loss_db=atmospheric_loss_db,
        received_power_dbm=round(rx_power_dbm, 1),
        noise_floor_dbm=round(noise_dbm, 1),
        snr_db=round(snr_db, 1), margin_db=round(margin, 1),
        max_data_rate_bps=round(max_rate, 0), ber=ber,
    )


if __name__ == "__main__":
    # UHF link
    uhf = calculate_link_budget(
        frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
        rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
    )
    print(f"UHF Link: SNR={uhf.snr_db} dB, Margin={uhf.margin_db} dB, BER={uhf.ber:.2e}")

    # S-band link
    sband = calculate_link_budget(
        frequency_mhz=2400, tx_power_w=2.0, tx_gain_dbi=6.0,
        rx_gain_dbi=20.0, distance_km=2000, data_rate_bps=256000,
    )
    print(f"S-band: SNR={sband.snr_db} dB, Margin={sband.margin_db} dB, BER={sband.ber:.2e}")
