# Message Format

Every part of the system (streamer, backend, ML model, 3D twin, simulation) exchanges data in this format. One message represents one reading of the classroom.

## Example message

```json
{
  "timestamp": "2026-09-01T10:15:00",
  "room_id": "classroom_1",
  "temperature": 25.4,
  "light": 120,
  "sound": 0.08,
  "co2": 360,
  "co2_slope": 0.0,
  "pir_1": 0,
  "pir_2": 1,
  "true_occupancy": 2
}
```

## Field descriptions

| Field | Unit | Source column(s) | Description |
|---|---|---|---|
| timestamp | ISO 8601 | Date + Time | When the reading was taken |
| room_id | text | (fixed value) | Identifier of the classroom, e.g. classroom_1 |
| temperature | °C | mean of S1_Temp, S2_Temp, S3_Temp, S4_Temp | Average room temperature |
| light | lux | mean of S1_Light, S2_Light, S3_Light, S4_Light | Average light level |
| sound | sensor units | mean of S1_Sound, S2_Sound, S3_Sound, S4_Sound | Average sound level |
| co2 | ppm | S5_CO2 | CO2 concentration |
| co2_slope | ppm per interval | S5_CO2_Slope | Rate of change of CO2 |
| pir_1 | 0 or 1 | S6_PIR | First motion sensor (1 = motion detected) |
| pir_2 | 0 or 1 | S7_PIR | Second motion sensor (1 = motion detected) |
| true_occupancy | people (0-3) | Room_Occupancy_Count | Ground-truth head count, used only for evaluation. The ML model must never take this as input. |

## Notes

- Data source: UCI Room Occupancy Estimation dataset (see README for citation).
- The streamer replays dataset rows as if they were live sensor readings.
- The original per-sensor columns (S1 to S4) stay available in the raw data for ML training.