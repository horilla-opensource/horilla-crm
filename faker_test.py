import json
from datetime import datetime

output_file = "forecast_type.json"


def generate_forecast_type_fixture(filename=output_file):
    base_date = datetime(2025, 5, 7, 18, 30)
    fixture_data = []

    forecast_entries = [
        {
            "name": "Revenue Amount Forecast",
            "forecast_type": "deal_revenue_amount",
            "description": "Forecast based on total deal revenue amount",
        },
        {
            "name": "Expected Revenue Forecast",
            "forecast_type": "deal_revenue_expected_amount",
            "description": "Forecast based on expected deal revenue amount",
        },
        {
            "name": "Quantity Forecast",
            "forecast_type": "deal_quantity",
            "description": "Forecast based on total deal quantity",
        },
    ]

    for pk, entry in enumerate(forecast_entries, start=1):
        record = {
            "model": "forecast.forecasttype",
            "pk": pk,
            "fields": {
                "name": entry["name"],
                "description": entry["description"],
                "forecast_type": entry["forecast_type"],
                "include_pipeline": True,
                "include_best_case": True,
                "include_commit": True,
                "include_closed": True,
                "is_active": True,
                "created_at": base_date.isoformat() + "Z",
                "updated_at": base_date.isoformat() + "Z",
                "created_by": 1,
                "updated_by": 1,
                "company": 1,
            },
        }
        fixture_data.append(record)

    with open(filename, "w") as f:
        json.dump(fixture_data, f, indent=4)

    print(f"✅ Generated {len(forecast_entries)} forecast types in '{filename}'")


# Run the generator
generate_forecast_type_fixture()
