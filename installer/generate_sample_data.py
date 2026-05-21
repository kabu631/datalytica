"""
Generate realistic sample CSV datasets for Datalytica testing.
Creates 3 different datasets covering different domains.
"""
import os
import random
import csv
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'sample_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# Dataset 1: E-Commerce Sales Data (500 rows)
# ─────────────────────────────────────────────────────────────────────────────
products = ["Laptop", "Phone", "Tablet", "Headphones", "Monitor", "Keyboard", "Mouse", "Webcam", "Speaker", "Charger"]
categories = {"Laptop": "Computers", "Phone": "Mobile", "Tablet": "Mobile",
              "Headphones": "Audio", "Monitor": "Displays", "Keyboard": "Peripherals",
              "Mouse": "Peripherals", "Webcam": "Accessories", "Speaker": "Audio", "Charger": "Accessories"}
regions = ["North", "South", "East", "West", "Central"]
payment = ["Credit Card", "PayPal", "Bank Transfer", "Crypto", None]  # None = missing value

start_date = datetime(2023, 1, 1)

with open(os.path.join(OUTPUT_DIR, "ecommerce_sales.csv"), "w", newline='') as f:
    w = csv.writer(f)
    w.writerow(["order_id", "date", "product", "category", "region", "quantity", "unit_price", "revenue", "payment_method", "customer_age", "discount_pct"])
    for i in range(1, 501):
        product = random.choice(products)
        qty = random.randint(1, 10)
        price = round(random.uniform(9.99, 1499.99), 2)
        disc = random.choice([0, 0, 0, 5, 10, 15, 20])
        revenue = round(qty * price * (1 - disc / 100), 2)
        date = (start_date + timedelta(days=random.randint(0, 730))).strftime('%Y-%m-%d')
        age = random.randint(18, 72) if random.random() > 0.05 else None  # 5% nulls
        pay = random.choice(payment)
        w.writerow([f"ORD-{i:04d}", date, product, categories[product],
                    random.choice(regions), qty, price, revenue, pay, age, disc])

print("✅ ecommerce_sales.csv created (500 rows)")

# ─────────────────────────────────────────────────────────────────────────────
# Dataset 2: HR / Employee Data (300 rows)
# ─────────────────────────────────────────────────────────────────────────────
departments = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations", "Legal"]
job_levels = ["Junior", "Mid", "Senior", "Lead", "Manager", "Director"]
cities = ["New York", "London", "Kathmandu", "Tokyo", "Sydney", "Berlin", "Toronto"]

with open(os.path.join(OUTPUT_DIR, "employee_data.csv"), "w", newline='') as f:
    w = csv.writer(f)
    w.writerow(["employee_id", "name", "department", "job_level", "salary", "years_experience",
                "city", "performance_score", "is_remote", "join_date", "satisfaction_rating"])
    first_names = ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Sam", "Chris", "Jamie", "Drew",
                   "Priya", "Liam", "Aisha", "Wei", "Carlos", "Sofia", "Anya", "Marcus", "Nadia", "Rohan"]
    last_names  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Sharma", "Patel"]

    for i in range(1, 301):
        dept = random.choice(departments)
        level = random.choice(job_levels)
        base_salary = {"Junior": 35000, "Mid": 55000, "Senior": 75000,
                       "Lead": 90000, "Manager": 110000, "Director": 140000}[level]
        salary = round(base_salary * random.uniform(0.85, 1.25), 2)
        exp = random.randint(0, 25)
        perf = round(random.gauss(3.5, 0.8), 1)
        perf = max(1.0, min(5.0, perf))
        # Introduce some outlier salaries
        if random.random() < 0.03:
            salary *= 3
        satisfaction = random.randint(1, 10) if random.random() > 0.08 else None
        join = (start_date + timedelta(days=random.randint(-1825, 0))).strftime('%Y-%m-%d')
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        w.writerow([f"EMP-{i:04d}", name, dept, level, salary, exp,
                    random.choice(cities), perf, random.choice([True, False]), join, satisfaction])

print("✅ employee_data.csv created (300 rows)")

# ─────────────────────────────────────────────────────────────────────────────
# Dataset 3: Daily Weather / IoT Sensor Data (365 rows - 1 year)
# ─────────────────────────────────────────────────────────────────────────────
with open(os.path.join(OUTPUT_DIR, "weather_sensors.csv"), "w", newline='') as f:
    w = csv.writer(f)
    w.writerow(["date", "station_id", "temperature_c", "humidity_pct", "wind_kmh",
                "rainfall_mm", "pressure_hpa", "uv_index", "air_quality_index", "weather_condition"])
    conditions = ["Sunny", "Cloudy", "Rainy", "Windy", "Stormy", "Foggy", "Partly Cloudy"]

    for day in range(365):
        date = (datetime(2023, 1, 1) + timedelta(days=day)).strftime('%Y-%m-%d')
        month = int(date[5:7])
        # Seasonal temperature variation
        base_temp = 15 + 12 * __import__('math').sin((month - 3) * 3.14 / 6)
        temp = round(base_temp + random.gauss(0, 4), 1)
        humidity = round(random.uniform(30, 95), 1)
        wind = round(random.exponential(15), 1) if random.random() > 0.1 else None  # 10% nulls
        rain = round(random.exponential(3), 2) if random.random() < 0.3 else 0
        pressure = round(random.gauss(1013, 15), 1)
        uv = random.randint(0, 11)
        aqi = random.randint(20, 200)
        cond = random.choice(conditions)
        w.writerow([date, f"STN-{random.randint(1,5):02d}", temp, humidity,
                    wind, rain, pressure, uv, aqi, cond])

print("✅ weather_sensors.csv created (365 rows)")
print()
print("=" * 50)
print("All sample datasets created in: sample_data/")
print("=" * 50)
