"""
Function to generate ndjson files of various sizes
"""
from __future__ import annotations

import ndjson
from faker import Faker

fake = Faker()


# Define function to generate fake data and store into a NDJSON file
def generate_data(file_name, records):
    customer = [
        {
            "id": n,
            "name": fake.name(),
            "address": fake.address(),
            "email": str(fake.email()),
            "phone": str(fake.phone_number()),
        }
        for n in range(0, records)
    ]
    # Write the data into the NDJSON file
    with open(file_name, "w") as fp:
        ndjson.dump(customer, fp)

    print(f"File {file_name} has been created.")


# create ten_kb ndjson file
ten_kb = "fake_dataset/ndjson/ten_kb.ndjson"
ten_kb_rows = 67
generate_data(ten_kb, ten_kb_rows)

# create hundred_kb ndjson file
hundred_kb = "/fake_dataset/ndjson/hundred_kb.ndjson"
hundred_kb_rows = 601
generate_data(hundred_kb, hundred_kb_rows)

# create hundred_mb ndjson file
hundred_mb = "/fake_dataset/ndjson/hundred_mb.ndjson"
hundred_mb_rows = 591336
generate_data(hundred_mb, hundred_mb_rows)

# create ten_mb ndjson file
ten_mb = "/fake_dataset/ndjson/ten_mb.ndjson"
ten_mb_rows = 59324
generate_data(ten_mb, ten_mb_rows)

# create one_mb ndjson file
one_mb = "/fake_dataset/ndjson/one_mb.ndjson"
one_mb_rows = 6483
generate_data(one_mb, one_mb_rows)

# create one_gb ndjson file
one_gb = "/fake_dataset/ndjson/one_gb.ndjson"
one_gb_rows = 5993353
generate_data(one_gb, one_gb_rows)

# create two_gb ndjson file
two_gb = "/fake_dataset/ndjson/two_gb.ndjson"
two_gb_rows = 14794706
generate_data(two_gb, two_gb_rows)
