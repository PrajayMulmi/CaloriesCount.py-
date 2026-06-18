#!/usr/bin/env python3
"""
Macro Tracker CLI — tracks protein, carbs, fats, and calories
using the Open Food Facts API (no API key required).
"""
 
import json
import os
import urllib.request
import urllib.parse
from datetime import date
from typing import Optional
 
# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
LOG_FILE = "macro_log.json"
 
DAILY_GOALS = {
    "calories": 2000,
    "protein_g": 150,
    "carbs_g": 200,
    "fat_g": 65,
}
 
 
# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────
def empty_macros() -> dict:
    return {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
 
 
def scale(macros: dict, grams: float) -> dict:
    """Scale macros from per-100g values to actual serving size."""
    factor = grams / 100.0
    return {k: round(v * factor, 2) for k, v in macros.items()}
 
 
def add_macros(a: dict, b: dict) -> dict:
    return {k: round(a[k] + b[k], 2) for k in a}
 
 
# ──────────────────────────────────────────────
# OPEN FOOD FACTS API
# ──────────────────────────────────────────────
OFF_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_FIELDS = "product_name,nutriments,serving_size"
 
 
def search_food(query: str, max_results: int = 5) -> list[dict]:
    """Search Open Food Facts and return a list of products with macros per 100 g."""
    params = urllib.parse.urlencode({
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": max_results,
        "fields": OFF_FIELDS,
    })
    url = f"{OFF_SEARCH}?{params}"
 
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MacroTrackerCLI/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [API error] {e}")
        return []
 
    results = []
    for product in data.get("products", []):
        name = product.get("product_name", "").strip()
        if not name:
            continue
        n = product.get("nutriments", {})
        macros = {
            "calories":  float(n.get("energy-kcal_100g") or n.get("energy_100g", 0) or 0),
            "protein_g": float(n.get("proteins_100g", 0) or 0),
            "carbs_g":   float(n.get("carbohydrates_100g", 0) or 0),
            "fat_g":     float(n.get("fat_100g", 0) or 0),
        }
        results.append({"name": name, "macros_per_100g": macros})
 
    return results
 
 
# ──────────────────────────────────────────────
# LOG PERSISTENCE
# ──────────────────────────────────────────────
def load_log() -> dict:
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return {}
 
 
def save_log(log: dict) -> None:
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)
 
 
def today_key() -> str:
    return str(date.today())
 
 
def get_today_entries(log: dict) -> list[dict]:
    return log.get(today_key(), [])
 
 
def add_entry(log: dict, entry: dict) -> None:
    key = today_key()
    log.setdefault(key, []).append(entry)
    save_log(log)
 
 
def today_totals(log: dict) -> dict:
    totals = empty_macros()
    for entry in get_today_entries(log):
        totals = add_macros(totals, entry["macros"])
    return totals
 
 
# ──────────────────────────────────────────────
# DISPLAY HELPERS
# ──────────────────────────────────────────────
SEP = "─" * 52
 
 
def print_header(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)
 
 
def print_macros(macros: dict, label: str = "") -> None:
    prefix = f"{label}: " if label else ""
    print(f"  {prefix}"
          f"Cal {macros['calories']:.0f} kcal  |  "
          f"Protein {macros['protein_g']:.1f}g  |  "
          f"Carbs {macros['carbs_g']:.1f}g  |  "
          f"Fat {macros['fat_g']:.1f}g")
 
 
def print_progress_bar(label: str, current: float, goal: float, width: int = 20) -> None:
    pct = min(current / goal, 1.0) if goal else 0
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    print(f"  {label:<10} [{bar}] {current:.0f} / {goal:.0f}  ({pct*100:.0f}%)")
 
 
def print_summary(log: dict) -> None:
    totals = today_totals(log)
    entries = get_today_entries(log)
 
    print_header(f"Today's Log — {today_key()}")
    if not entries:
        print("  No foods logged yet.")
    else:
        for i, e in enumerate(entries, 1):
            print(f"  {i}. {e['name']}  ({e['grams']}g)")
            print_macros(e["macros"], label="    ")
    print()
    print("  ── TOTALS ──")
    print_progress_bar("Calories", totals["calories"],  DAILY_GOALS["calories"])
    print_progress_bar("Protein",  totals["protein_g"], DAILY_GOALS["protein_g"])
    print_progress_bar("Carbs",    totals["carbs_g"],   DAILY_GOALS["carbs_g"])
    print_progress_bar("Fat",      totals["fat_g"],     DAILY_GOALS["fat_g"])
    print()
 
 
# ──────────────────────────────────────────────
# COMMANDS
# ──────────────────────────────────────────────
def cmd_search_and_log(log: dict) -> None:
    query = input("\n  Search food: ").strip()
    if not query:
        return
 
    print("  Searching Open Food Facts…")
    results = search_food(query)
 
    if not results:
        print("  No results found. Try a different search term.")
        return
 
    print_header("Search Results")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['name']}")
        print_macros(r["macros_per_100g"], label="     per 100g")
 
    choice = input("\n  Select a number (or 0 to cancel): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(results):
        print("  Invalid selection.")
        return
 
    selected = results[idx]
    grams_str = input(f"  How many grams of '{selected['name']}'? ").strip()
    try:
        grams = float(grams_str)
    except ValueError:
        print("  Invalid number.")
        return
 
    macros = scale(selected["macros_per_100g"], grams)
    entry = {"name": selected["name"], "grams": grams, "macros": macros}
    add_entry(log, entry)
 
    print(f"\n  ✓ Logged {grams}g of {selected['name']}")
    print_macros(macros)
 
 
def cmd_add_custom(log: dict) -> None:
    print_header("Add Custom Food")
    name = input("  Food name: ").strip() or "Custom food"
    try:
        grams    = float(input("  Serving size (g): ") or 100)
        calories = float(input("  Calories (kcal):  ") or 0)
        protein  = float(input("  Protein (g):      ") or 0)
        carbs    = float(input("  Carbs (g):        ") or 0)
        fat      = float(input("  Fat (g):          ") or 0)
    except ValueError:
        print("  Invalid input — entry not saved.")
        return
 
    macros = {"calories": calories, "protein_g": protein, "carbs_g": carbs, "fat_g": fat}
    entry = {"name": name, "grams": grams, "macros": macros}
    add_entry(log, entry)
    print(f"\n  ✓ Logged custom entry: {name}")
 
 
def cmd_set_goals() -> None:
    print_header("Set Daily Goals")
    print("  (Press Enter to keep current value)")
    for key, current in DAILY_GOALS.items():
        val = input(f"  {key} [{current}]: ").strip()
        if val:
            try:
                DAILY_GOALS[key] = float(val)
            except ValueError:
                print(f"  Skipping {key} — invalid value.")
    print("\n  ✓ Goals updated for this session.")
 
 
def cmd_history(log: dict) -> None:
    print_header("History (last 7 days)")
    if not log:
        print("  No history yet.")
        return
    for day_key in sorted(log.keys(), reverse=True)[:7]:
        entries = log[day_key]
        totals = empty_macros()
        for e in entries:
            totals = add_macros(totals, e["macros"])
        print(f"\n  {day_key}  ({len(entries)} entries)")
        print_macros(totals)
 
 
def cmd_delete_entry(log: dict) -> None:
    entries = get_today_entries(log)
    if not entries:
        print("\n  No entries to delete.")
        return
 
    print_header("Delete Entry")
    for i, e in enumerate(entries, 1):
        print(f"  {i}. {e['name']}  ({e['grams']}g)")
 
    choice = input("\n  Entry number to delete (0 to cancel): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    idx = int(choice) - 1
    if 0 <= idx < len(entries):
        removed = entries.pop(idx)
        log[today_key()] = entries
        save_log(log)
        print(f"  ✓ Removed: {removed['name']}")
    else:
        print("  Invalid selection.")
 
 
# ──────────────────────────────────────────────
# MAIN MENU
# ──────────────────────────────────────────────
MENU = """
  [1] Search & log food (Open Food Facts)
  [2] Add custom food manually
  [3] View today's summary
  [4] View history
  [5] Delete a today's entry
  [6] Set daily goals
  [0] Quit
"""
 
 
def main() -> None:
    print("\n╔══════════════════════════════════════╗")
    print("║        🥗  Macro Tracker CLI          ║")
    print("╚══════════════════════════════════════╝")
 
    log = load_log()
 
    while True:
        print(MENU)
        choice = input("  Choice: ").strip()
 
        if choice == "1":
            cmd_search_and_log(log)
        elif choice == "2":
            cmd_add_custom(log)
        elif choice == "3":
            print_summary(log)
        elif choice == "4":
            cmd_history(log)
        elif choice == "5":
            cmd_delete_entry(log)
        elif choice == "6":
            cmd_set_goals()
        elif choice == "0":
            print("\n  Goodbye! Stay on track. 💪\n")
            break
        else:
            print("  Unknown option — try again.")
 
