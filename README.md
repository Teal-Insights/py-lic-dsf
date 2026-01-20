# LIC DSF Python package

## Usage

We currently export four public functions for computing critical output rows from each of three stress test tabs: B1_GDP_ext, B3_Exports_ext, and B4_other flows_ext.

``` python
from lic_dsf.entrypoint import (
    compute_b1_pv_of_ppg_external_debt_to_gdp_ratio,
    compute_b1_pv_of_ppg_external_debt_to_exports_ratio,
    compute_b1_ppg_debt_service_to_exports_ratio,
    compute_b1_ppg_debt_service_to_revenue_ratio,
    compute_b3_pv_of_ppg_external_debt_to_gdp_ratio,
    compute_b3_pv_of_ppg_external_debt_to_exports_ratio,
    compute_b3_ppg_debt_service_to_exports_ratio,
    compute_b3_ppg_debt_service_to_revenue_ratio,
    compute_b4_pv_of_ppg_external_debt_to_gdp_ratio,
    compute_b4_pv_of_ppg_external_debt_to_exports_ratio,
    compute_b4_ppg_debt_service_to_exports_ratio,
    compute_b4_ppg_debt_service_to_revenue_ratio
)
```

Each function takes either inputs or context. To change inputs, import the `DEFAULT_INPUTS` and assign new values to cells by Excel cell address. (In a future version of the library, we will provide more ergonomic helpers for manipulating inputs.)

```python
from lic_dsf.inputs import DEFAULT_INPUTS

print(compute_b1_pv_of_ppg_external_debt_to_gdp_ratio(inputs=DEFAULT_INPUTS))
```

> {'B1_GDP_ext!C36:B1_GDP_ext!X36': array([[105.10651096132852, 109.06466686131711, 103.46892335626711, 99.556231343041, 98.4191890680463, 95.29727410995618, 93.70930948475184, 89.4654309833856, 84.95596608942697, 83.87385668256111, 83.52798038607628, 83.65374794444864, 83.92646092458857, 83.72091267061994, 83.28225539226987, 83.06839367915266, 83.32378011757078, 82.45746746506089, 81.63149410584113, 80.27958003061562, 79.47482897016569, 78.54394783711992]], dtype=object)}