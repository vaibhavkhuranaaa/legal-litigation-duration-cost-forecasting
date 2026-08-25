# Synthetic staffing and budget scenarios

Scenario outputs are deterministic sensitivities, not observed bills or real cost forecasts. Users supply matter count, planning horizon, monthly attorney and paralegal hours per matter, hourly rates, productive hours per FTE, and low/high multipliers.

The engine returns low, base, and high cases with total hours, FTE requirements, and budget in USD. Every response includes `scenario_type: synthetic`, `observed_cost_data_used: false`, the full assumption set, and a limitation statement.

Input bounds prevent accidental unbounded calculations. Identical assumptions produce byte-equivalent values after cents rounding.
