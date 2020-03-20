def mailbox_data():
    return [
        {"section": "Capture", "endpoints": [
            {"name": "displayCapture", "args": ["str usr_uid", "JCapture cap", "list<JDevicePoint> points" ], "chatty": True },
            {"name": "requestActiveCapture", "args": ["int test", "long other test"], "qml_only": True },
            {"name": "activeCapture", "args": ["JCaptureStorageInfo capture", "list<JDevicePoint> points"], "remote": True },
            {"name": "setInteractionStatus", "args": ["bool capture", "int visibility"] },
        ]},
]
