from csv import DictReader
from typing import Dict
from os.path import dirname, realpath


def get_country_dict_by_2alpha() -> Dict[str, Dict[str, str]]:
  with open(
    dirname(realpath(__file__)) + "/wb_list_country.csv", mode="r", encoding="utf-8"
  ) as csv_file:
    csv_reader = DictReader(csv_file, delimiter=";")

    countries = dict()
    for row in csv_reader:
      countries[row["code_2alpha"]] = row

  return countries


def get_nuts_by_code() -> Dict[str, Dict[str, str]]:
  with open(
    dirname(realpath(__file__)) + "/list_nuts_codes.csv", mode="r", encoding="utf-8"
  ) as csv_file:
    csv_reader = DictReader(csv_file, delimiter=";")

    countries = dict()
    for row in csv_reader:
      countries[row["code_nuts"]] = row

  return countries


def get_nuts_translation() -> Dict[str, Dict[str, str]]:
  with open(
    dirname(realpath(__file__)) + "/list_nuts_translation.csv",
    mode="r",
    encoding="utf-8",
  ) as csv_file:
    csv_reader = DictReader(csv_file, delimiter=";")

    countries = dict()
    for row in csv_reader:
      countries[row["code_nuts"]] = row

  return countries
