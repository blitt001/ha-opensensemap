# OpenSenseMap Uploader for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/blitt001/ha-opensensemap)](https://github.com/blitt001/ha-opensensemap/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Upload** your weather station and air quality data from Home Assistant to [OpenSenseMap](https://opensensemap.org/).

This integration allows you to contribute measurements from your personal weather station or environmental sensors (temperature, humidity, pressure, PM2.5, PM10) to the OpenSenseMap citizen science network - using any sensors connected to Home Assistant.

> **Note:** This integration **uploads** data TO OpenSenseMap. It is different from the built-in Home Assistant `opensensemap` integration which only **reads** data FROM the network.

## Features

- **Simple UI Configuration** - Easy setup through Home Assistant's integration UI
- **Flexible Sensor Mapping** - Map any HA sensor to OpenSenseMap sensor IDs
- **Automatic Uploads** - Configurable interval-based data pushing (default: 5 minutes)
- **Status Monitoring** - Track upload status, errors, and upload history
- **Optional Authentication** - Support for access token authentication
- **Automatic Unit Conversion** - Converts temperature, pressure, and humidity units automatically
- **Debug Mode** - View exact API requests for troubleshooting

## Supported Measurements

| Measurement | Notes |
|-------------|-------|
| PM2.5 | Particulate Matter 2.5μm |
| PM10 | Particulate Matter 10μm |
| Temperature | Auto-converts °F to °C |
| Humidity | In % |
| Pressure | Auto-converts hPa/mbar/inHg/psi to Pa |

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu and select **Custom repositories**
4. Add this repository URL: `https://github.com/blitt001/ha-opensensemap`
5. Select **Integration** as the category
6. Click **Install**
7. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/opensensemap` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **OpenSenseMap**
4. Follow the setup wizard:
   - Enter your SenseBox ID (24-character hex string)
   - Optionally enter your access token
   - Map your Home Assistant sensors to OpenSenseMap sensor IDs
   - Configure update interval (default: 5 minutes, minimum: 1 minute)

## Getting Your SenseBox and Sensor IDs

1. Log in to your account at [opensensemap.org](https://opensensemap.org/account)
2. Select your SenseBox
3. The **SenseBox ID** is the 24-character string in the URL or on the box details page
4. Click on each sensor to find its **Sensor ID** (also a 24-character hex string)

Example IDs:
- SenseBox ID: `5a1b2c3d4e5f6a7b8c9d0e1f`
- Sensor ID: `5a1b2c3d4e5f6a7b8c9d0e2a`

## How It Works

The integration sends a single API call per update cycle containing all configured sensor values:

```
POST https://api.opensensemap.org/boxes/{boxId}/data
```

Payload format:
```json
{
  "sensorId1": "value1",
  "sensorId2": "value2"
}
```

## Status Sensor

The integration creates a status sensor with `device_class: enum`. The entity ID is based on your SenseBox ID, for example: `sensor.opensensemap_5a1b2c3d_status`.

### Sensor States

| State | Description |
|-------|-------------|
| `pending` | Integration started, waiting for first upload |
| `ok` | Last upload was successful |
| `error` | Upload failed or sensors unavailable |

### Attributes

| Attribute | Description |
|-----------|-------------|
| `box_id` | Your SenseBox ID |
| `upload_count` | Number of successful uploads |
| `last_upload` | Timestamp of last successful upload |
| `next_upload` | Timestamp of next scheduled upload |
| `last_error` | Last error message (if any) |
| `last_request` | Request details (debug mode only) |

## Unit Conversions

The integration automatically detects and converts units based on the sensor's `unit_of_measurement` attribute:

| Measurement | Input Unit | Output Unit | Conversion |
|-------------|------------|-------------|------------|
| Temperature | °F | °C | (°F - 32) × 5/9 |
| Temperature | °C | °C | No conversion |
| Pressure | hPa, mbar | Pa | × 100 |
| Pressure | inHg | Pa | × 3386.39 |
| Pressure | psi | Pa | × 6894.76 |
| Pressure | Pa | Pa | No conversion |
| Humidity | 0-1 (decimal) | % | × 100 |
| Humidity | 0-100 (%) | % | No conversion |

## Logging

The integration logs important events to the Home Assistant log:

| Level | Event |
|-------|-------|
| `WARNING` | Sensors unavailable, upload skipped |
| `ERROR` | HTTP error (4xx/5xx response) |
| `ERROR` | Request timeout |
| `ERROR` | Network connection error |

Example log entries:
```
WARNING - Skipping OpenSenseMap upload - sensors unavailable: ['sensor.bme280_temperature']
ERROR - Failed to push data to OpenSenseMap: 401 - Unauthorized
ERROR - Timeout pushing data to OpenSenseMap
```

### Enable Debug Logging

To enable detailed debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.opensensemap: debug
```

Restart Home Assistant after adding this configuration.

## Automations

You can create automations based on the status sensor state changes.

### Example: Send notification on error

```yaml
alias: Notify OpenSenseMap Upload Error
description: Send notification when upload fails
triggers:
  - trigger: state
    entity_id: sensor.opensensemap_5a1b2c3d_status  # Replace with your entity ID
    to: "error"
conditions: []
actions:
  - action: notify.notify
    data:
      title: "OpenSenseMap Upload Failed"
      message: "Error: {{ state_attr('sensor.opensensemap_5a1b2c3d_status', 'last_error') }}"
```

### Example: Log when upload recovers

```yaml
alias: Log OpenSenseMap Recovery
triggers:
  - trigger: state
    entity_id: sensor.opensensemap_5a1b2c3d_status  # Replace with your entity ID
    from: "error"
    to: "ok"
actions:
  - action: system_log.write
    data:
      message: "OpenSenseMap upload recovered after error"
      level: info
```

## Authentication

Some SenseBoxes require authentication to post data. If your box requires it:

1. Go to your SenseBox settings on opensensemap.org
2. Generate or find your access token
3. Enter it during integration setup or in the options flow

## Troubleshooting

### Data not appearing on OpenSenseMap

1. Check the status sensor for errors
2. Enable debug mode in the integration options
3. Verify your SenseBox ID and sensor IDs are correct
4. Check if your box requires authentication

### HTTP 401 Unauthorized

Your box requires authentication. Add your access token in the integration configuration.

### HTTP 422 Unprocessable Entity

Check that your sensor IDs are correct and match the sensors configured in your SenseBox.

### Invalid Box ID or Sensor ID

Both IDs must be 24-character hexadecimal strings (e.g., `5a1b2c3d4e5f6a7b8c9d0e1f`).

## Requirements

- Home Assistant 2024.1.0 or newer

## License

MIT License - see [LICENSE](LICENSE) for details.
