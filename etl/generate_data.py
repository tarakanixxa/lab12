"""Відтворюваний генератор синтетичних виробничих даних. Seed=20261123."""
import random
from datetime import date, timedelta
import pandas as pd

SEED = 20261123
N_FACTS = 5000

def generate():
    rng = random.Random(SEED)
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(365)]
    machines = [
        (1, "CNC-01", "Токарний ЧПК 01", "CNC lathe", "DMG CTX", "Механічна майстерня", "Метал-Деталь"),
        (2, "CNC-02", "Токарний ЧПК 02", "CNC lathe", "Haas ST-20", "Механічна майстерня", "Метал-Деталь"),
        (3, "CNC-03", "Токарний ЧПК 03", "CNC lathe", "Doosan Lynx", "Механічна майстерня", "Метал-Деталь"),
        (4, "MILL-01", "Фрезерний центр 01", "CNC milling", "Haas VF-2", "Механічна майстерня", "Метал-Деталь"),
    ]
    products = [
        (1, "SHAFT-001", "Вал приводний", "Вали", "Сталь", "45"),
        (2, "SHAFT-002", "Вал проміжний", "Вали", "Сталь", "45"),
        (3, "SHAFT-003", "Вал ступінчастий", "Вали", "Сталь", "45"),
        (4, "BUSH-001", "Втулка напрямна", "Втулки", "Сталь", "45"),
    ]
    ops = [
        (1, "Механічна обробка", "https://example.org/industry/operation#Machining", "Точіння", "https://example.org/industry/operation#Turning", "Чорнове точіння"),
        (2, "Механічна обробка", "https://example.org/industry/operation#Machining", "Точіння", "https://example.org/industry/operation#Turning", "Чистове точіння"),
        (3, "Механічна обробка", "https://example.org/industry/operation#Machining", "Фрезерування", "https://example.org/industry/operation#Milling", "Фрезерування пазу"),
        (4, "Контроль якості", "https://example.org/industry/operation#QualityControl", "Вимірювання", "https://example.org/industry/operation#Measurement", "Контроль розмірів"),
    ]
    shifts = [(1, "Ранкова", 6, 14), (2, "Вечірня", 14, 22), (3, "Нічна", 22, 6)]
    facts = []
    for i in range(1, N_FACTS + 1):
        dt = rng.choice(dates)
        m = rng.choice(machines)
        p = rng.choice(products)
        op = rng.choice(ops)
        sh = rng.choice(shifts)
        qty = rng.randint(20, 180)
        defect_rate = rng.uniform(0.005, 0.075) + (0.025 if m[0] == 3 else 0)
        defect = min(qty, round(qty * defect_rate))
        good = qty - defect
        cycle = {1: 1.7, 2: 1.25, 3: 1.9, 4: 0.45}[op[0]]
        machine_minutes = qty * cycle * rng.uniform(0.9, 1.15)
        downtime = max(0, rng.gauss(12, 9))
        material = qty * ({1: 1.8, 2: 1.5, 3: 2.1, 4: 0.65}[p[0]]) * rng.uniform(1.01, 1.12)
        facts.append((i, dt, m[0], p[0], op[0], sh[0], f"B-{dt:%y%m%d}-{i:05d}",
                      qty, good, defect, round(machine_minutes, 2),
                      round(material, 3), round(downtime, 2)))
    return machines, products, ops, shifts, dates, facts

if __name__ == "__main__":
    *_, facts = generate()
    print(f"Generated {len(facts)} production records using seed={SEED}")
