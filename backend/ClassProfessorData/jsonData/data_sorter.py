import pandas as pd
import math
import statistics
import json

"""
This file includes functions to sort all the class data into two seperate Jsons

Another one for professors
{
    "professorId": "nameCS123",
    "metadata": {
        "name": "name",
    },
    "classesTaught": [
    {
        "classsId": "CS123",
        "classGradeDistribution": {
        "AP": 1,
        "A": 1,
        "AM": 1,
        "B": 2,
        "C": 5,
        "D": 0,
        "F": 0
        },
        "classStats": {
        "averageGrade": 3.8,
        "averageTotalStudents": 10
    },

        
    ],

    "professorGradeDistribution": {
        "AP": 1,
        "A": 1,
        "AM": 1,
        "B": 2,
        "C": 5,
        "D": 0,
        "F": 0
        },
    "professorStats": {
        "averageGrade": 3.8,
        "averageTotalStudents": 10
    }
}
"""

def classCsvToJson(csvFile):
  """
  This function will take a csv file and convert it to a json file
  The csv file should have the following columns:
  - classId
  - name
  - professors
  - gradeDistribution
  - stats

  The json file will have the following structure:
  
  "classId": "CS123"
  {
    "name": "CS123",
    "professors": [
      {
        "id": "profCS123",
        "name": "name"
      }
    ],
    "gradeDistribution": {
      "AP": 1,
      "A": 1,
      "AM": 1,
      "B": 2,
      "C": 5,
      "D": 0,
      "F": 0
    },
    "stats": {
      "averageGrade": 3.8,
      "averageTotalStudents": 10
    }
  }

  The json file will be saved to the data/jsonData/classes.json file

  The json file will be used to store the class data
  """
  class_data = {}
  df = pd.read_csv(csvFile)
  for index, row in df.iterrows():
    course_id = row["course_id"].strip()
    course_id = course_id.replace(" ", "")
    class_data[course_id] = {
      "course_id": row["course_id"],
      "course_number": row["course_number"],
      "total_students": row["total_students"],
      "gradeDistribution": {
        "AP": row["AP"],
        "A": row["A"],
        "AM": row["AM"],
        "BP": row["BP"],
        "B": row["B"],
        "BM": row["BM"],
        "CP": row["CP"],
        "C": row["C"],
        "CM": row["CM"],
        "DP": row["DP"],
        "D": row["D"],
        "DM": row["DM"],  
        "F": row["F"]
      },
      "stats": {
        "averageGrade": row["avg_gpa"],
        "totalStudents": row["total_students"]
      }
    }
  with open("deg_guide/data/jsonData/classes.json", "w") as f:
    json.dump(class_data, f)
  print("Classes data saved to deg_guide/data/jsonData/classes.json")
  return class_data

def professorToJson(csvFile, course_professor_csv):
  professor_data = {}
  df = pd.read_csv(csvFile)
  for index, row in df.iterrows():
    professor_id = row["professor"].strip()
    professor_id = professor_id.replace(" ", "")
    professor_data[professor_id] = {
      "professor_name": row["professor"],
      "courses_taught_count": row["courses_taught_count"],
      "courses_taught": row["courses_taught"],
      "gradeDistribution": {
        "AP": row["AP"],
        "A": row["A"],
        "AM": row["AM"],
        "BP": row["BP"],
        "B": row["B"],
        "BM": row["BM"],
        "CP": row["CP"],
        "C": row["C"],
        "CM": row["CM"],
        "DP": row["DP"],
        "D": row["D"],
        "DM": row["DM"],  
        "F": row["F"],
        "A_Count": row["A_count"],
        "B_Count": row["B_count"],
        "C_Count": row["C_count"],
        "D_Count": row["D_count"],
        "F_Count": row["F_count"],
      },
      "stats": {
        "averageGrade": row["avg_gpa"],
        "totalStudents": row["total_students"]
      }
    }
  with open("ClassProfessorData/jsonData/professors.json", "w") as f:
    json.dump(professor_data, f)
  print("Professors data saved to ClassProfessorData/jsonData/professors.json")
  return professor_data


if __name__ == "__main__":
  class_data = classCsvToJson("ClassProfessorData/courses.csv") #change this to the csv file you want to convert
  professor_data = professorToJson("ClassProfessorData/professors.csv", "ClassProfessorData/course_professor.csv") #change this to the csv file you want to convert
  



