def api_data():
    return [
      {
        "name": "capture",
        "endpoints": [
          {"name": "create", "resp": "JCaptureCreate", "err": "JErr", "args": [
            "str name",
            "str visibility",
            "str timezone",
            "long start_ts",
            "long finish_ts",
            "list<str> device_uids",
            "list<str> radius_uids"
          ]},
          {"name": "exists", "resp": "JCaptureExists", "err": "JErr", "args": [ "str capture_uid" ]},
        ]
      },
    ]
