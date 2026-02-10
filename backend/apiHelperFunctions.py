import pandas as pd
import json

def classFinder(class_id):
    with open("deg_guide/data/jsonData/classes.json", "r") as f:
        class_data = json.load(f)
    print(class_data[class_id])
    return class_data[class_id]

def professorFinder(professor_id):
    with open("deg_guide/data/jsonData/professors.json", "r") as f:
        professor_data = json.load(f)
    print(professor_data)
    return professor_data[professor_id]

