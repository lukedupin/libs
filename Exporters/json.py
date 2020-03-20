def struct_data():
    return [
        { "name": "JHuman",
          "fields": [
            "str name",
            "int age",
            "float lat",
            "float lng",
            "bool admin",
            "long created_on",
          ]
        },
        { "name": "JHumanList",
          "fields": [
              "list<JHuman> humans",
          ]
        },
      ]
