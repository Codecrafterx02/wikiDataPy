

import requests
import os
from dotenv import load_dotenv
from writer import WikiWriter
import json
import csv

from time import sleep
load_dotenv()


class BulkWriter(WikiWriter):

    DELTA = 2

    def addClaimsFromCSV(self, fileSource: str, header: bool = True, delimiter=",", outputFile=None):
        """
        Create a new claim on a Wikidata entity.\n
        *Claims of type entity_id, property_id, value_id*

        :param fileSource: str, the path  of the CSV file having data as entity_id, property_id,value_id
        :param header:  boolean specifying if csv file has header or not
        :param delimiter:  source csv file separator
        :param outputFile:  CSV file to store result
        """

        if not self.csrf_token:
            print("You have no CSRF token, kindly login and then call getCSRFToken()")
            return

        try:
            with open(fileSource, "r") as f:
                reader = csv.reader(f)

                if header:  # header set
                    next(reader)

                resp = []
                fields = ["id", "entity_id", "property_id", "value_id"]
                csvData = []
                for i in reader:
                    dt = {"entity_id": i[0],
                          "property_id": i[1], "value_id": i[2]}
                    x = self.addClaim(i[0], i[1], i[2])

                    dt["id"] = ""
                    if "claim" in x and "id" in x["claim"]:
                        dt["id"] = x["claim"]["id"]

                    resp.append(x)
                    csvData.append(dt)

                if outputFile:
                    if outputFile.endswith(".json"):
                        WikiWriter.dumpResult(resp, outputFile)

                    elif outputFile.endswith(".csv"):
                        WikiWriter.dumpCSV(outputFile, fields, csvData)
                    else:
                        print("Invalid output file specified. Specify JSON/CSV")
                return resp

        except Exception as e:
            print("Error", e)
            return e

    def createEntitiesFromCSV(self, fileSource: str, header: bool = True, delimiter: str = ",", outputFile: str = "created.csv"):
        """
        Create a new  Wikidata entity per row in CSV file

        :param fileSource: str, the path  of the CSV file having
        :param header:  boolean specifying if csv file has header or not
        :param delimiter:  source csv file separator
        :param outputFile:  store results here


        CSV file format of rows (with optional header but specify if header present)
        language_code_1,label_1,description_1,alias1,language_code2,label_2,description2,alias2,... so on for desired languages


        where alias1 is pipe joined aliases

        this creates one entity per row with a  labels descriptions specified
        for multiple labels/descriptions in more than one language , create 1 entity then use 'editEntitiesFromCSV' 
        from entities' ids
        """

        if not self.csrf_token:
            print("You have no CSRF token, kindly login and then call getCSRFToken()")
            return

        try:
            writeRes = []
            with open(fileSource, "r") as f:
                reader = csv.reader(f, delimiter=delimiter)

                if header:  # header set
                    hdr = list(next(reader))
                    hdr.insert(0, "id")
                    writeRes.append(hdr)

                resp = []
                for i in reader:

                    # create labels descriptions using triplets
                    lbl = {}
                    desc = {}
                    aliases = {}
                    for j in range(3, len(i), 4):
                        lbl[i[j-3]] = i[j-2]
                        desc[i[j-3]] = i[j-1]
                        if i[j]:
                            aliases[i[j-3]] = i[j].split('|')

                    if not aliases:
                        aliases = None
                    x = self.createOrEditEntity(lbl, desc, aliases)
                    curr = list(i)
                    if not x or "error" in x:
                        curr.insert(0, -1)

                    elif "entity" in x and "id" in x["entity"]:
                        curr.insert(0, x["entity"]["id"])

                    else:
                        curr.insert(0, -1)

                    resp.append(x)
                    writeRes.append(curr)
                    sleep(BulkWriter.DELTA)

                # write results to other CSV

                if not outputFile or type(outputFile) != str:
                    print("Invalid output file format specify JSON/CSV")

                elif outputFile.endswith('.csv'):

                    with open(outputFile, mode="w", newline="") as f2:
                        writer = csv.writer(f2)
                        writer.writerows(writeRes)
                elif outputFile.endswith('.json'):
                    WikiWriter.dumpResult(resp, outputFile)
                return resp

        except Exception as e:
            print("Error", e)
            return e
        finally:
            print(
                "If facing limit issues try after few time or increase BulkWriter.DELTA")

    def editEntitiesFromCSV(self, fileSource: str, header: bool = True, delimiter=",", outputFile: str = ""):
        """
        Performs a edit on Wikidata entity per row in CSV file specified by entity_id

        :param fileSource: str, the path  of the CSV file having
        :param header:  boolean specifying if csv file has header or not (default True)
        :param delimiter:  source csv file separator
        :param outputFile:  CSV file to store status of edits


        CSV file format of rows (with optional header but specify if header present) 
        (can have multiple rows of same entity_id specifying different language label, description)
        entity_id,language_code,label,description,aliases

        """

        if not self.csrf_token:
            print("You have no CSRF token, kindly login and then call getCSRFToken()")
            return

        try:
            with open(fileSource, "r") as f:
                reader = csv.reader(f, delimiter=delimiter)

                if header:  # header set
                    next(reader)

                resp = []
                hdr = ["id", "success"]
                csvDt = []
                for i in reader:
                    x = self.createOrEditEntity(
                        {i[1]: i[2]}, {i[1]: i[3]}, {i[1]: i[4].split("|")}, i[0])
                    if "entity" in x and "success" in x:
                        csvDt.append(
                            {"id": x["entity"]["id"],  "success": x["success"]})
                    resp.append(x)

                    # sleep(BulkWriter.DELTA)
                if outputFile and type(outputFile) == str and outputFile.endswith(".csv"):
                    WikiWriter.dumpCSV(outputFile, hdr, csvDt)
                return resp

        except Exception as e:
            print("Error", e)
            return e
        finally:
            print(
                "If facing limit issues try after few time or increase BulkWriter.DELTA")


def bulk_add_claim_test(w: BulkWriter):
    f1 = "demo/4_Addclaims.csv"
    f2 = "demo/4_AddClaims_result.csv"
    res = w.addClaimsFromCSV(f1, outputFile=f2)
    print("Bulk done")


def bulk_create_entities(w: BulkWriter):
    # f1 = "bulk/test_create.csv"
    # f2 = "bulk/test_create_3.json"  # lot of creations
    # f1 = "bulk/testMul_create.csv"
    # f2 = "bulk/test_create_5Mul.json"  # lot of creations

    f1 = "demo/5_bulkCreateEntities.csv"
    f2 = "demo/5_bulkCreateResult.csv"  # lot of creations

    res = w.createEntitiesFromCSV(f1, outputFile=f2)
    print("Bulk Create done")
    # w.dumpResult(res, f2)


def bulk_edit_entities(w: BulkWriter):
    f1 = "demo/6_editEnt.csv"
    f2 = "demo/6_editEntResult.csv"

    res = w.editEntitiesFromCSV(f1, outputFile=f2)
    print("Bulk Edit done")
    # w.dumpResult(res, f2)


if __name__ == "__main__":

    # bulk add claim test

    w = BulkWriter(os.getenv("WIKI_USERNAME"), os.getenv("WIKI_PASSWORD"))
    w.login()
    w.getCSRFTtoken()

    # bulk_add_claim_test(w)

    # bulk_create_entities(w)

    bulk_edit_entities(w)

    w.logout()
