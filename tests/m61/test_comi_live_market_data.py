from tools.m61_market_validation import validate_history_points

# Real COMI daily observations surfaced from Investing.com historical data.
# Scope: 2026-09-01 through 2026-10-01.
COMI_ROWS = [
    {"date":"2026-09-01","open":137.02,"high":140.00,"low":137.02,"close":139.00,"volume":6545563},
    {"date":"2026-09-02","open":139.00,"high":139.50,"low":137.81,"close":138.98,"volume":1974218},
    {"date":"2026-09-03","open":138.99,"high":141.00,"low":138.81,"close":141.00,"volume":3102402},
    {"date":"2026-09-06","open":141.00,"high":142.50,"low":140.01,"close":142.00,"volume":2560000},
    {"date":"2026-09-07","open":142.11,"high":142.80,"low":140.06,"close":140.06,"volume":3870000},
    {"date":"2026-09-08","open":140.53,"high":141.00,"low":138.55,"close":138.55,"volume":3730000},
    {"date":"2026-09-09","open":139.50,"high":140.57,"low":138.13,"close":139.20,"volume":2290000},
    {"date":"2026-09-10","open":139.52,"high":139.58,"low":138.17,"close":138.17,"volume":5300000},
    {"date":"2026-09-13","open":137.00,"high":137.90,"low":136.05,"close":136.05,"volume":1840000},
    {"date":"2026-09-14","open":136.10,"high":136.50,"low":132.90,"close":133.32,"volume":5170000},
    {"date":"2026-09-15","open":133.32,"high":134.00,"low":131.56,"close":132.50,"volume":5460000},
    {"date":"2026-09-16","open":133.00,"high":133.47,"low":131.11,"close":131.75,"volume":2910000},
    {"date":"2026-09-17","open":131.78,"high":134.00,"low":131.31,"close":132.50,"volume":11410000},
    {"date":"2026-09-20","open":133.01,"high":134.50,"low":132.62,"close":133.69,"volume":1160000},
    {"date":"2026-09-21","open":133.06,"high":133.97,"low":132.49,"close":133.14,"volume":6900000},
    {"date":"2026-09-22","open":133.23,"high":133.45,"low":131.50,"close":131.50,"volume":7170000},
    {"date":"2026-09-23","open":132.00,"high":132.00,"low":128.10,"close":128.10,"volume":5460000},
    {"date":"2026-09-24","open":128.20,"high":128.73,"low":126.81,"close":128.20,"volume":4390000},
    {"date":"2026-09-27","open":129.94,"high":129.95,"low":128.50,"close":128.74,"volume":1120000},
    {"date":"2026-09-28","open":128.70,"high":130.00,"low":127.10,"close":128.50,"volume":2280000},
    {"date":"2026-09-29","open":128.55,"high":129.50,"low":128.01,"close":128.01,"volume":3660000},
    {"date":"2026-09-30","open":128.20,"high":128.20,"low":124.50,"close":126.30,"volume":4400000},
    {"date":"2026-10-01","open":126.30,"high":128.15,"low":126.25,"close":127.69,"volume":3150000},
]


def test_real_comi_market_data_passes_project_validation():
    assert len(COMI_ROWS) == 23
    assert validate_history_points(COMI_ROWS) == []
