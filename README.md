# enverus-developer-api

[![PyPI version](https://badge.fury.io/py/enverus-developer-api.svg)](https://badge.fury.io/py/enverus-developer-api)

A thin wrapper around Enverus' Developer API. Handles authentication and token management, pagination and
network-related error handling/retries.  

This module is built and tested on Python 3.9 but should work on Python 2.7 and up.


## Install
```commandline
pip install enverus-developer-api
```

## Clients

### Developer API - Version 3
DirectAccess has been rebranded as DeveloperAPI. For version 3 of the API, create an instance of the DeveloperAPIv3 class, providing it your secret_key (not the same as the v2 api_key).
The returned access token will be available as an attribute on the instance (v3.access_token) and the Authorization
header is set automatically.
```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(secret_key='<your-secret-key>')
```
Your secret_key can be generated, retrieved and revoked at https://app.enverus.com/provisioning/directaccess

The Developer API Version 3 endpoint documentation can be found at https://app.enverus.com/direct/#/api/explorer/v3/gettingStarted

### Direct Access - Version 2
For version 2 of the API, create an instance of the DirectAccessV2 class, providing it your API key, client id and client secret.
The returned access token will be available as an attribute on the instance (d2.access_token) and the Authorization
header is set automatically
```python
from enverus_developer_api import DirectAccessV2

d2 = DirectAccessV2(
    api_key='<your-api-key>',
    client_id='<your-client-id>',
    client_secret='<your-client-secret>',
)
```
The Direct Access Version 2 endpoint documentation can be found at https://app.enverus.com/direct/#/api/explorer/v2/gettingStarted

## Usage

The functionality outlined below exists for **both** DeveloperAPIv3 and DirectAccessV2 clients.

Only 1 instance of the client needs to be created to perform all your queries. It can execute multiple simultaneous requests if needed,
and will automatically refresh the access_token for the Authorization header if expired.
An access_token is valid for 8 hours, and there is rate limit on the number of access_tokens that can be requested per minute
which is why we recommend creating and reusing a single DeveloperAPIv3 client instance for all of your querying.

Provide the query method the dataset and query params. All query parameters must match the valid
Request Parameters found in the Developer API documentation for a given dataset and be passed as keyword arguments.

```python
for row in v3.query('wells', county='REEVES', deleteddate='null'):
    print(row)
```

### Filter functions
Developer API supports filter functions. These can be passed as strings on the keyword arguments.

Some common filters are greater than (`gt()`), less than (`lt()`), null, not null (`not(null)`) and between (`btw()`).  
See the Developer API documentation for a list of all available filters.

```python
# Get well records updated after 2018-08-01 and without deleted dates
for row in v3.query('wells', updateddate='gt(2018-08-01)', deleteddate='null'):
    print(row)

# Get permit records with approved dates between 2018-03-01 and 2018-06-01
for row in v3.query('rigs', spuddate='btw(2018-03-01,2018-06-01)'):
    print(row) 
```

You can use the `fields` keyword to limit the returned fields in your request.

```python
for row in v3.query('rigs', fields='PermitApprovedDate,LeaseName,RigName_Number,MD_FT'):
    print(row)
```

### Escaping
When making requests containing certain characters like commas, use a backslash to escape them.

```python
# Escaping the comma before LLC
for row in v3.query('rigs', envoperator='PERCUSSION PETROLEUM OPERATING\, LLC'):
    print(row)
```

### Network request handling
This module exposes functionality in python-requests for modifying network requests handling, namely:
* retries and backoff
* network proxies
* ssl verification

#### Retries and backoff
Specify the number of retry attempts in `retries` and the backoff factor in `backoff_factor`. See the urllib3
[Retry](https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.Retry) utility API for more info
```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    retries=5,
    backoff_factor=1
)
```

You can specify a network proxy by passing a dictionary with the host and port of your proxy to `proxies`. See the
[proxies](https://requests.readthedocs.io/en/master/user/advanced/#proxies) section of the python-requests documentation
for more info.
```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    proxies={'https': 'http://10.10.1.10:1080'}
)
```

Finally, if you're in an environment that provides its own SSL certificates that might not be in your trusted store,
you can choose to ignore SSL verification altogether. This is typically not a good idea and you should seek to resolve
certificate errors instead of ignore them.
```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    verify=False
)
```

## Functions

### docs
Returns a sample response for a given dataset
```python
docs = v3.docs("casings")
```

### ddl
Returns a CREATE TABLE DDL statement for a given dataset. Must specify either 
"mssql" for MS SQL Server or "pg" for PostgreSQL as the database argument
```python
from tempfile import TemporaryFile

ddl = v3.ddl("casings", database="pg")
with TemporaryFile(mode="w+") as f:
  f.write(ddl)
  f.seek(0)
  for line in f:
    print(line, end='')
```

### count
Returns the count of records for a given dataset and query options in the 
X-QUERY-RECORD-COUNT response header value
```python
count = v3.count("rigs", deleteddate="null")
```

### query
Accepts a dataset name, request headers and a variable number of keyword arguments that correspond to the fields specified 
in the ‘Request Parameters’ section for each dataset in the Developer API documentation.

This method only supports the JSON output provided by the API and yields dicts for each record
```python
for row in v3.query("rigs", pagesize=1000, deleteddate="null"):
    print(row)
```
##### X-Omit-Header-Next-Links header
Omit the Next Link in the Response Header section, add the Next Link to the JSON Response Body.
```python
for row in v3.query("rigs", pagesize=1000, deleteddate="null", _headers={'X-Omit-Header-Next-Links': 'true'}):
    print(row)
```

### to_csv
Write query results to CSV. Optional keyword arguments are provided to the csv writer object, 
allowing control over delimiters, quoting, etc. The default is comma-separated with csv.QUOTE_MINIMAL
```python
import csv, os
from tempfile import mkdtemp

tempdir = mkdtemp()
path = os.path.join(tempdir, "rigs.csv")

dataset = "rigs"
options = dict(pagesize=10000, deleteddate="null")

v3.query(dataset, **options)
v3.to_csv(query, path, log_progress=True, delimiter=",", quoting=csv.QUOTE_MINIMAL)

with open(path, mode="r") as f:
  reader = csv.reader(f)
```

### to_dataframe
Write query results to a pandas Dataframe with properly set dtypes and index columns.

This works by requesting the DDL for a given dataset and manipulating the text to build a list of dtypes, date columns and the index column(s). 
It then makes a query request for the dataset to ensure we know the exact fields to expect, 
(ie, if fields was a provided query parameter and the result will have fewer fields than the DDL).

For endpoints with composite primary keys, a pandas MultiIndex is created.

Query results are written to a temporary CSV file and then read into the dataframe. The CSV is removed afterwards.

Pandas version 0.24.0 or higher is required for use of the Int64 dtype allowing integers with NaN values. 
It is not possible to coerce missing values for columns of dtype bool and so these are set to dtype object.

You will need to have pandas installed to use the to_dataframe function
```python
pip install pandas
```

Create a pandas dataframe from a dataset query
```python
df = v3.to_dataframe("rigs", pagesize=10000, deleteddate="null")
```

Create a Texas rigs dataframe, replacing the state abbreviation with the complete name
and removing commas from Operator names
```python
df = v3.to_dataframe(
  dataset="rigs",
  deleteddate="null",
  pagesize=100000,
  stateprovince="TX",
  converters={
    "StateProvince": lambda x: "TEXAS",
    "ENVOperator": lambda x: x.replace(",", "")
  }
)
df.head(10)
```
Reset the index of the DataFrame, and use the default one instead. [reset_index()](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.reset_index.html)
```python
    df = v3.to_dataframe(dataset, pagesize=10000, ENVBasin="SACRAMENTO")
    df.reset_index(inplace=True)
    df.head(10)
```