"""Platform for sensor integration."""
from __future__ import annotations

import logging
import string
from datetime import timedelta
from typing import Callable, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA, SensorStateClass, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, UnitOfVolume, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .Invoices import InvoicesList, Invoices
from .Energa24Api import Energa24Api
from .PpgReadingForMeter import MeterReading

_LOGGER = logging.getLogger(__name__)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})
SCAN_INTERVAL = timedelta(hours=8)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities,
):
    user = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    api = Energa24Api(user, password)
    try:
        pgps = await hass.async_add_executor_job(api.meterList)
    except Exception:
        raise ValueError

    # Extract client/account info from the API response
    client_id = pgps.client_number
    account_id = pgps.account_number

    for x in pgps.ppg_list:
        meter_id = x.ppe_number
        id_local = int(x.mp_id_dms) if x.mp_id_dms else 0
        async_add_entities(
            [Energa24Sensor(hass, api, meter_id, id_local, account_id, client_id),
             Energa24InvoiceSensor(hass, api, meter_id, id_local, account_id, client_id),
             Energa24CostTrackingSensor(hass, api, meter_id, id_local, account_id, client_id)],
            update_before_add=True)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    api = Energa24Api(config.get(CONF_USERNAME), config.get(CONF_PASSWORD))
    try:
        pgps = await hass.async_add_executor_job(api.meterList)
    except Exception:
        raise ValueError

    # Use data from API for consistency
    client_id = pgps.client_number
    account_id = pgps.account_number

    for x in pgps.ppg_list:
        meter_id = "{}-{}-{}".format(x.ppe_number, client_id, account_id)
        id_local = int(x.mp_id_dms) if x.mp_id_dms else 0
        async_add_entities(
            [Energa24Sensor(hass, api, meter_id, id_local, account_id, client_id),
             Energa24InvoiceSensor(hass, api, meter_id, id_local, account_id, client_id),
             Energa24CostTrackingSensor(hass, api, meter_id, id_local, account_id, client_id)],
            update_before_add=True)


class Energa24Sensor(SensorEntity):
    def __init__(self, hass, api: Energa24Api, meter_id: string,
                 id_local: int, account_number: str, client_number: str) -> None:
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._state: MeterReading | None = None
        self.hass = hass
        self.api = api
        self.meter_id = meter_id
        self.id_local = id_local
        self.account_number = account_number
        self.client_number = client_number
        self.entity_name = "Energa24 Energy Sensor " + meter_id + " " + str(id_local)

    @property
    def unique_id(self) -> str | None:
        return "energa24_sensor" + self.meter_id + "_" + str(self.id_local)

    @property
    def device_info(self):
        return {
            "identifiers": {("energa24_energy_sensor", self.meter_id)},
            "name": f"Energa24 ENERGY METER ID {self.meter_id}",
            "manufacturer": "Energa24",
            "model": self.meter_id,
            "via_device": None,
        }

    @property
    def name(self) -> str:
        return self.entity_name

    @property
    def state(self):
        if self._state is None:
            return None
        return self._state.value

    @property
    def extra_state_attributes(self):
        attrs = dict()
        if self._state is not None:
            attrs["wear"] = self._state.wear
            attrs["wear_unit_of_measurment"] = UnitOfEnergy.KILO_WATT_HOUR
        return attrs

    async def async_update(self):
        latest_meter_reading: MeterReading = await self.hass.async_add_executor_job(self.latestMeterReading)
        self._state = latest_meter_reading

    def latestMeterReading(self):
        readings = self.api.readingForMeter(self.meter_id, self.account_number, self.client_number).meter_readings
        if not readings:
            return None
        return max(readings, key=lambda z: z.reading_date_utc)


class Energa24InvoiceSensor(SensorEntity):
    def __init__(self, hass, api: Energa24Api, meter_id: str, id_local: int, account_number: str,
                 client_number: str) -> None:
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state: InvoicesList | None = None
        self.hass = hass
        self.api = api
        self.meter_id = meter_id
        self.id_local = id_local
        self.entity_name = "Energa24 Energy Invoice Sensor " + meter_id + " / " + str(id_local)
        self.account_number = account_number
        self.client_number = client_number

    @property
    def unique_id(self) -> str | None:
        return "energa24_invoice_sensor" + self.meter_id + "_" + str(self.id_local)

    @property
    def device_info(self):
        return {
            "identifiers": {("energa24_energy_sensor", self.meter_id)},
            "name": f"Energa24 ENERGY METER ID {self.meter_id}",
            "manufacturer": "Energa24",
            "model": self.meter_id,
            "via_device": None,
        }

    @property
    def name(self) -> str:
        return self.entity_name

    @property
    def state(self):
        if self._state is None:
            return None
        return self._state.get("sumOfUnpaidInvoices")

    @property
    def extra_state_attributes(self):
        attrs = dict()
        if self._state is not None:
            attrs["next_payment_date"] = self._state.get("nextPaymentDate")
            attrs["next_payment_amount_to_pay"] = self._state.get("nextPaymentAmountToPay")
            attrs["next_payment_wear"] = self._state.get("nextPaymentWear")
            attrs["next_payment_wear_KWH"] = self._state.get("nextPaymentWearKWH")
        return attrs

    async def async_update(self):
        self._state = await self.hass.async_add_executor_job(self.invoices_summary)

    def invoices_summary(self):

        def upcoming_payment_for_meter(x: Invoices):
            return self.meter_id == x.id_pp

        def to_amount_to_pay(x: Invoices):
            return x.amount_to_pay

        # Get the list of invoices
        invoices_response = self.api.invoices(account_number=self.account_number, client_number=self.client_number)
        invoices_list = invoices_response.invoices_list

        # Use None as default instead of failing InvoicesList instantiation
        next_payment_item = min(filter(upcoming_payment_for_meter, invoices_list),
                                key=lambda z: z.date,
                                default=None)

        sum_of_unpaid_invoices = sum(map(to_amount_to_pay, filter(upcoming_payment_for_meter, invoices_list)))

        # Safe access to attributes if item exists
        return {
            "sumOfUnpaidInvoices": sum_of_unpaid_invoices,
            "nextPaymentDate": next_payment_item.paying_deadline_date if next_payment_item else None,
            "nextPaymentWear": next_payment_item.wear if next_payment_item else None,
            "nextPaymentWearKWH": next_payment_item.wear_kwh if next_payment_item else None,
            "nextPaymentAmountToPay": next_payment_item.amount_to_pay if next_payment_item else None
        }


class Energa24CostTrackingSensor(SensorEntity):
    def __init__(self, hass, api: Energa24Api, meter_id: string,
                 id_local: int, account_number: str, client_number: str) -> None:
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state: InvoicesList | None = None
        self.hass = hass
        self.api = api
        self.meter_id = meter_id
        self.id_local = id_local
        self.entity_name = "Energa24 Energy Cost Tracking Sensor " + meter_id + " / " + str(id_local)
        self.account_number = account_number
        self.client_number = client_number

    @property
    def unique_id(self) -> str | None:
        return "energa24_cost_tracking_sensor" + self.meter_id + "_" + str(self.id_local)

    @property
    def device_info(self):
        return {
            "identifiers": {("energa24_energy_sensor", self.meter_id)},
            "name": f"Energa24 ENERGY METER ID {self.meter_id}",
            "manufacturer": "Energa24",
            "model": self.meter_id,
            "via_device": None,
        }

    @property
    def name(self) -> str:
        return self.entity_name

    @property
    def state(self):
        return 1234

    @property
    def extra_state_attributes(self):
        attrs = dict()
        if self._state is not None:
            attrs["last_invoice_date"] = self._state.paying_deadline_date
            attrs["last_invoice_gross_amount"] = self._state.gross_amount
            attrs["last_invoice_wear"] = self._state.wear
            attrs["last_invoice_wear_KWH"] = self._state.wear_kwh
        return attrs

    async def async_update(self):
        self._state = await self.hass.async_add_executor_job(self.latest_price)

    def latest_price(self):
        meter_id = self.meter_id

        def upcoming_payment_for_meter(x: InvoicesList):
            return str(meter_id) == x.id_pp \
                and x.wear is not None \
                and x.wear != 0 \
                and x.gross_amount is not None \
                and x.gross_amount != 0

        invoices_response = self.api.invoices(account_number=self.account_number, client_number=self.client_number)

        return max(filter(upcoming_payment_for_meter, invoices_response.invoices_list),
                   key=lambda z: z.date,
                   default=None)
