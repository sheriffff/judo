from analyse import run_informe_competitor
from db import conn

comps = conn.as_pandas('select * from competitors where category="men_66"', parse_dates=['last_extraction'])
comps.head()

errors = []

for index, comp in comps.iterrows():
    try:
        print(f"Running informe for {comp['name']}")
        run_informe_competitor(comp['profile_id'])
    except:
        errors.append((comp['name'], comp['profile_id']))

print(errors)
