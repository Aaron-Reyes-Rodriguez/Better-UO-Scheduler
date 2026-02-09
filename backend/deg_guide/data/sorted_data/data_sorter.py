import pandas as pd
import math
import statistics

"""
This file includes functions to sort all the class data into two seperate Jsons

One Json is for every class
{
  "classId": "CS123",
  "metadata": {
    "name": "CS123",
  },
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

def classSorter (csvFile):
    pass

def professorSorter(csvFile):
    pass

def findAvgGrade(gradeDict, totalStudents):
    """
    {AP: 1, A: 2, AM: 4}

    (4.3*1) + (4.0*2) + (3.7*4) = NUM
    ret NUM/4
    """
    
    return

def findAvgClassSize(studentList):
    """
    [10, 10, 7] -> 9
    """
    return statistics.mean(studentList)


