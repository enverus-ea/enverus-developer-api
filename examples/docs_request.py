# This code allows you to generate a csv containing the DDL for each endpoint by cycling through a list of the endpoints

# create a file called secretkey.txt with your secret key
with open("secretkey.txt", "r") as file:
    private_key = file.read()
import csv 
import json
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(secret_key=private_key)

# This code pulls from a file called endpoints.txt containing the names of each endpoint
with open('endpoints.txt') as f:
    for line in f:
        print(line.strip())
        docs = v3.docs(line)
        # Counter variable used for writing
        # headers to the CSV file
        count = 0
        # now we will open a file for writing
        data_file = open(line.strip() + '.csv', 'w')
        
        # create the csv writer object
        csv_writer = csv.writer(data_file)        
        for emp in docs:
            if count == 0:
        
                # Writing headers of CSV file
                header = emp.keys()
                csv_writer.writerow(header)
                count += 1
        
            # Writing data of CSV file
            csv_writer.writerow(emp.values())
        
        data_file.close()
