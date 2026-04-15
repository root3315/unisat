"""Tests for the link budget calculator module."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from link_budget_calculator import SPEED_OF_LIGHT, calculate_link_budget


class TestUHFLinkBudget:
    """Tests for UHF band link budget."""

    def test_uhf_positive_margin(self):
        budget = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        assert budget.margin_db > 0, f"UHF margin {budget.margin_db} dB should be positive"

    def test_uhf_snr_positive(self):
        budget = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        assert budget.snr_db > 0

    def test_uhf_ber_below_threshold(self):
        budget = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        assert budget.ber < 1e-5, f"UHF BER {budget.ber:.2e} too high"


class TestSBandLinkBudget:
    """Tests for S-band link budget."""

    def test_sband_ber_below_threshold(self):
        budget = calculate_link_budget(
            frequency_mhz=2400, tx_power_w=2.0, tx_gain_dbi=6.0,
            rx_gain_dbi=20.0, distance_km=2000, data_rate_bps=256000,
        )
        assert budget.ber < 1e-3, f"S-band BER {budget.ber:.2e} too high"

    def test_sband_positive_margin(self):
        budget = calculate_link_budget(
            frequency_mhz=2400, tx_power_w=2.0, tx_gain_dbi=6.0,
            rx_gain_dbi=20.0, distance_km=2000, data_rate_bps=256000,
        )
        assert budget.margin_db > 0


class TestFreeSpaceLoss:
    """Tests for free space path loss calculation."""

    def test_fspl_increases_with_distance(self):
        near = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=500, data_rate_bps=9600,
        )
        far = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        assert far.free_space_loss_db > near.free_space_loss_db

    def test_fspl_increases_with_frequency(self):
        uhf = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        sband = calculate_link_budget(
            frequency_mhz=2400, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        assert sband.free_space_loss_db > uhf.free_space_loss_db


class TestMaxDataRate:
    """Tests for Shannon capacity estimate."""

    def test_max_data_rate_reasonable(self):
        budget = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        # Shannon capacity should exceed the design data rate
        assert budget.max_data_rate_bps > 9600

    def test_sband_higher_capacity_than_uhf(self):
        uhf = calculate_link_budget(
            frequency_mhz=437, tx_power_w=1.0, tx_gain_dbi=0.0,
            rx_gain_dbi=14.0, distance_km=2000, data_rate_bps=9600,
        )
        sband = calculate_link_budget(
            frequency_mhz=2400, tx_power_w=2.0, tx_gain_dbi=6.0,
            rx_gain_dbi=20.0, distance_km=2000, data_rate_bps=256000,
        )
        assert sband.max_data_rate_bps > uhf.max_data_rate_bps
