#!/usr/bin/python3

import json, time, re, sys, os
from api import api_data

def namify(name):
  return ''.join([x.capitalize() for x in name.split('_')])

def tTot( btype ):
    btype = re.sub(r"^str", "QString", btype)
    btype = re.sub(r"^float", "double", btype)
    btype = re.sub(r"^list", "QList", btype)
    btype = re.sub(r"^long", "qint64", btype)
    btype = re.sub(r"^bool", "bool", btype)
    btype = re.sub(r"<str>", "<QString>", btype)
    btype = re.sub(r"<int>", "<int>", btype)
    btype = re.sub(r"<bool>", "<bool>", btype)
    btype = re.sub(r"<float>", "<double>", btype)
    btype = re.sub(r"<long>", "<qint64>", btype)
    return btype

def tTotQml( btype ):
    btype = re.sub(r"^list<.*>", "QVariantList", btype)
    btype = re.sub(r"^str", "QString", btype)
    btype = re.sub(r"^int", "int", btype)
    btype = re.sub(r"^bool", "bool", btype)
    btype = re.sub(r"^long", "qint64", btype)
    btype = re.sub(r"^float", "double", btype)
    return btype

def read_value( btype, name, padding = "" ):
    # list?
    match = re.search(r'^list<(.+)>', btype)
    if match is not None:
        if read_value(match[1], name) == name:
            return "QJsonArray::fromVariantList( Primitive<%s>::toArray( &%s ))" % (tTot( match[1] ), name)
        else:
            return "%s::toArray( &%s )" % (match[1], name)

    # Base type, just output the name
    if re.search(r'^str', btype) is not None or \
       re.search(r'^int', btype) is not None or \
       re.search(r'^float', btype) is not None or \
       re.search(r'^bool', btype) is not None or \
       re.search(r'^long', btype) is not None:
        return name

    # Whatever else it is, it needs to handle exportValue();
    return '%s.toJson()' % (name)

def read_value_qml( btype, name, padding = "" ):
    #Base type, just output the name
    if re.search(r'^str', btype) is not None or \
       re.search(r'^int', btype) is not None or \
       re.search(r'^bool', btype) is not None or \
       re.search(r'^float', btype) is not None or \
       re.search(r'^long', btype) is not None:
        return name

    # Whatever else it is, it needs to handle exportValue();
    return 'variantToQJsonValue( %s )' % (name)


def handle( js, output_dir ):
    #js = json.loads( " ".join(open( schema ).exportlines()) )
    dir = output_dir + "/"

    ### Output api.h
    out = open(dir+"Net/net_api.h", "w")
    out.write("// Generated file.\n")
    out.write("// Edit CodeGenerators/api.py, then run ./export_api.py ..\n\n")
    out.write("#ifndef NET_API_H\n")
    out.write("#define NET_API_H\n")
    out.write("\n")
    out.write('#include <Json/json_struct.h>\n')
    out.write('#include <Net/network_http.h>\n')
    out.write('#include <QJSValue>\n')
    for section in js:
        out.write("\n")
        out.write("class Api%s\n" % namify( section['name']) )
        out.write("{\n")
        out.write("    private:\n")
        out.write("    NetworkHttp* _http = nullptr;\n")
        out.write("\n")
        out.write("    public:\n")
        out.write("    Api%s( NetworkHttp* http );\n" % namify( section['name']) )

        for ep in section['endpoints']:
            out.write("\n")

            #Short form template
            if len(ep['args']) > 0:
                args = [tTot(x) for x in ep['args']]
                out.write("    void %s( %s,\n" % (ep['name'], ', '.join(args)))
            else:
                out.write("    void %s(\n" % (ep['name']))
            out.write("             std::function<void (%s&)> success = nullptr,\n" % ep['resp'])
            out.write("             std::function<void (%s&, bool)> failed = nullptr );\n" % ep['err'])

        out.write("};\n")

        out.write("\n")
        out.write("class Api%sQml : public QObject\n" % namify( section['name']) )
        out.write("{\n")
        out.write("    Q_OBJECT\n")
        out.write("\n")
        out.write("    private:\n")
        out.write("    NetworkHttp* _http = nullptr;\n")
        out.write("    QJSEngine* _engine = nullptr;\n")
        out.write("\n")
        out.write("    public:\n")
        out.write("\n")
        out.write("    void loadEngine( NetworkHttp* http, QJSEngine* engine );\n")

        for ep in section['endpoints']:
            out.write("\n")
            if len(ep['args']) > 0:
                args = [tTotQml(x) for x in ep['args']]
                out.write("    Q_INVOKABLE void %s( %s,\n" % (ep['name'], ', '.join(args)))
            else:
                out.write("    Q_INVOKABLE void %s(\n" % (ep['name']))
            out.write("                             QJSValue success = QJSValue(), QJSValue failed = QJSValue() );\n")
            #out.write("                             QJSValue success = QJSValue(), QJSValue failed = QJSValue(), QJSValue timeout = QJSValue() );\n")
        out.write("};\n")

    # Create the header for the main api object
    out.write("\n")
    out.write("class ApiInterface : public QObject\n")
    out.write("{\n")
    out.write("    Q_OBJECT\n")
    out.write("\n")
    out.write("    private:\n")
    out.write("    NetworkHttp* _http = nullptr;\n")
    out.write("    bool _networkOnline = false;\n")
    out.write("\n")
    out.write("    public:\n")
    out.write("\n")
    out.write("    static const int MAJOR = 1;\n")
    out.write("    static const int MINOR = 0;\n")
    out.write("\n")
    out.write("    ApiInterface( NetworkHttp* http, Mailbox* mailbox );\n")
    out.write("\n")
    out.write("    void loadEngine( QJSEngine* engine );\n")
    out.write("\n")
    out.write("    Q_INVOKABLE bool isOnline();\n")
    out.write("\n")
    for section in js:
        out.write("    Api%s %s;\n" % (namify( section['name']), namify( section['name'])))
    for section in js:
        out.write("\n")
        out.write("    Q_PROPERTY( Api%sQml* %s READ _%s )\n" % (namify( section['name']), namify( section['name']), section['name']))
        out.write("    Api%sQml _%sQml;\n" % (namify( section['name']), section['name']))
        out.write("    Api%sQml* _%s();\n" % (namify( section['name']), section['name']))
    out.write("\n")
    out.write("    private slots:\n")
    out.write("\n")
    out.write("    void onNetworkStatusChanged( bool online );\n")

    #Wrap up and give the user the api struct register call
    out.write("};\n")
    out.write("\n")
    out.write("#endif\n")
    out.close()




    ### Write out api.cpp

    out = open(dir+"Net/net_api.cpp", "w")
    out.write("// Generated file.\n")
    out.write("// Edit CodeGenerators/api.py, then run ./export_api.py ..\n\n")
    out.write("#ifdef API_PICKER\n")
    out.write('#include <functional>\n')
    out.write('#include <Net/net_api.h>\n')
    out.write('#include <Json/json_struct.h>\n')
    out.write('#include <Util/api_util.h>\n')
    out.write('#include <QQmlEngine>\n')
    for section in js:
        out.write("\n")
        out.write("Api%s::Api%s( NetworkHttp* network ) : _http( network ) {}\n" % (namify( section['name']), namify( section['name'])) )
        for ep in section['endpoints']:
            out.write("\n")

            if len(ep['args']) > 0:
                args = [tTot(x) for x in ep['args']]
                out.write("void Api%s::%s( %s,\n" % (namify( section['name']), ep['name'], ', '.join(args)))
            else:
                out.write("void Api%s::%s(\n" % (namify( section['name']), ep['name']))

            out.write("                std::function<void (%s&)> success,\n" % ep['resp'])
            out.write("                std::function<void (%s&, bool)> failed )\n" % ep['err'])
            out.write("{\n")
            out.write("    auto&& data = QJsonObject();\n")
            for arg in ep['args']:
                ary = arg.split(' ')
                out.write('    data.insert("%s", %s);\n' % (ary[-1], read_value(ary[0], ary[-1])))
            out.write('    _http->post( "/%s/%s/", data,\n' % (section['name'], ep['name']))
            out.write('                 [=](QJsonObject& js) {\n')
            out.write('                     auto json_result = false;\n')
            out.write('                     auto resp = %s::fromJson( &js, &json_result );\n' % (ep['resp']))
            out.write('                     if ( !json_result ) {\n')
            out.write('                         qDebug("Failed to map json /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                         auto err_result = false;\n')
            out.write('                         auto err = %s::fromJson( &js, &err_result );\n' % ep['err'])
            out.write('                         if ( failed != nullptr )\n')
            out.write('                             failed( err, false );\n')
            out.write('                         else if ( err_result )\n')
            out.write('                             qDebug("Error on /%s/%s/: %%s", err.reason.toLatin1().data());\n' % (section['name'], ep['name']))
            out.write('                         else\n')
            out.write('                             qDebug("Error without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                         return;\n')
            out.write('                     }\n')
            out.write('                     if ( success != nullptr )\n')
            out.write('                         success( resp );\n')
            out.write('                     else\n')
            out.write('                         qDebug("Successful: /%s/%s/" );\n' % (section['name'], ep['name']))
            out.write('                 },\n')
            out.write('                 [=](QJsonObject& js ) {\n')
            out.write('                     auto err_result = false;\n')
            out.write('                     auto err = %s::fromJson( &js, &err_result );\n' % ep['err'])
            out.write('                     if ( failed != nullptr )\n')
            out.write('                         failed( err, false );\n')
            out.write('                     else if ( err_result )\n')
            out.write('                         qDebug("Error on /%s/%s/: %%s", err.reason.toLatin1().data());\n' % (section['name'], ep['name']))
            out.write('                     else\n')
            out.write('                         qDebug("Error without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                 },\n')
            out.write('                 [=]() {\n')
            out.write('                     if ( failed != nullptr )\n')
            out.write('                     {\n')
            out.write('                         JErr err;\n')
            out.write('                         err.successful = false;\n')
            out.write('                         err.reason = "Timeout occurred";\n')
            out.write('                         failed( err, true );\n')
            out.write('                     }\n')
            out.write('                     else\n')
            out.write('                         qDebug("Timeout without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                 } );\n')
            out.write("}\n")

        out.write("\n")
        out.write("void Api%sQml::loadEngine( NetworkHttp* http, QJSEngine* engine )\n" % namify( section['name']))
        out.write("{\n")
        out.write("    _http = http;\n")
        out.write("    _engine = engine;\n")
        out.write("}\n")

        for ep in section['endpoints']:
            out.write("\n")
            if len(ep['args']) > 0:
                args = [tTotQml(x) for x in ep['args']]
                out.write("void Api%sQml::%s( %s,\n" % (namify( section['name']), ep['name'], ', '.join(args)))
            else:
                out.write("void Api%sQml::%s(\n" % (namify( section['name']), ep['name']))
            out.write("                QJSValue success,\n")
            out.write("                QJSValue failed )\n")
            #out.write("                QJSValue failed,\n")
            #out.write("                QJSValue timeout )\n")
            out.write("{\n")
            out.write("    auto&& data = QJsonObject();\n")
            for arg in ep['args']:
                ary = arg.split(' ')
                out.write('    data.insert("%s", %s);\n' % (ary[-1], read_value_qml(ary[0], ary[-1])))
            out.write('    _http->post( "/%s/%s/", data,\n' % (section['name'], ep['name']))
            out.write('                 [=](QJsonObject& js) mutable {\n')
            out.write('                     auto json_result = false;\n')
            out.write('                     %s::fromJson( &js, &json_result );\n' % (ep['resp']))
            out.write('                     if ( !json_result ) {\n')
            out.write('                         qDebug("Failed to map json /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                         auto err_result = false;\n')
            out.write('                         auto err = %s::fromJson( &js, &err_result );\n' % ep['err'])
            out.write('                         if ( failed.isCallable() )\n')
            out.write('                             callQJSValue( failed, _engine, QJsonValue( js ) );\n')
            out.write('                         else if ( err_result )\n')
            out.write('                             qDebug("Error on /%s/%s/: %%s", err.reason.toLatin1().data());\n' % (section['name'], ep['name']))
            out.write('                         else\n')
            out.write('                             qDebug("Error without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                         return;\n')
            out.write('                     }\n')
            out.write('                     if ( success.isCallable() )\n')
            out.write('                         callQJSValue( success, _engine, QJsonValue( js ) );\n')
            out.write('                 },\n')
            out.write('                 [=](QJsonObject& js ) mutable {\n')
            out.write('                     auto err_result = false;\n')
            out.write('                     auto err = %s::fromJson( &js, &err_result );\n' % ep['err'])
            out.write('                     if ( failed.isCallable() )\n')
            out.write('                         callQJSValue( failed, _engine, QJsonValue( js ), QJsonValue( false ) );\n')
            out.write('                     else if ( err_result )\n')
            out.write('                         qDebug("Error on /%s/%s/: %%s", err.reason.toLatin1().data());\n' % (section['name'], ep['name']))
            out.write('                     else\n')
            out.write('                         qDebug("Error without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                 },\n')
            out.write('                 [=]() mutable {\n')
            #out.write('                     if ( timeout.isCallable() )\n')
            #out.write('                         callQJSValue( timeout, _engine );\n')
            #out.write('                     else if ( failed.isCallable() )\n')
            out.write('                     if ( failed.isCallable() )\n')
            out.write('                     {\n')
            out.write('                         %s err;\n' % ep['err'])
            out.write('                         err.successful = false;\n')
            out.write('                         err.reason = "Timeout occurred";\n')
            out.write('                         callQJSValue( failed, _engine, QJsonValue( err.toJson() ), QJsonValue( true ) );\n')
            out.write('                     }\n')
            out.write('                     else\n')
            out.write('                         qDebug("Timeout without callback on /%s/%s/");\n' % (section['name'], ep['name']))
            out.write('                 } );\n')
            out.write("}\n")

    # Build out my top level api call object
    out.write("\n")
    out.write("ApiInterface::ApiInterface( NetworkHttp* http, Mailbox* mailbox ) : \n")
    out.write('    _http( http ),\n')
    out.write('%s\n' % (',\n'.join(["    %s( http )" % namify( x['name']) for x in js])))
    out.write("{\n")
    out.write("    QObject::connect( mailbox, &Mailbox::networkStatusChanged, this, &ApiInterface::onNetworkStatusChanged );\n")
    out.write("}\n")

    out.write("\n")
    out.write("void ApiInterface::loadEngine( QJSEngine* engine )\n")
    out.write("{\n")
    for section in js:
        out.write('    qmlRegisterType<Api%sQml>( "Radius", 1, 0, "Api%sQml");\n' % (namify( section['name']), namify( section['name'])) )
    for section in js:
        out.write('    _%sQml.loadEngine( _http, engine );\n' % section['name'] )
    out.write("}\n")

    out.write("\n")
    out.write("bool ApiInterface::isOnline()\n")
    out.write("{\n")
    out.write("    return _networkOnline;\n")
    out.write("}\n")

    for section in js:
        out.write("\n")
        out.write("Api%sQml* ApiInterface::_%s()\n" % (namify( section['name']), section['name']))
        out.write("{\n")
        out.write('    return &_%sQml;\n' % section['name'] )
        out.write("}\n")

    out.write("\n")
    out.write("void ApiInterface::onNetworkStatusChanged( bool online )\n")
    out.write("{\n")
    out.write("    _networkOnline = online;\n")
    out.write("}\n")
    out.write("#endif\n")

    out.close()



    ### Output api_test.h
    out = open(dir+"Net/test_api.h", "w")
    out.write("// Generated file.\n")
    out.write("// Edit CodeGenerators/api.py, then run ./export_api.py ..\n\n")
    out.write("#ifndef TEST_API_H\n")
    out.write("#define TEST_API_H\n")
    out.write("\n")
    out.write('#include <Json/json_struct.h>\n')
    out.write('#include <Shared/mailbox.h>\n')
    out.write('#include <QQueue>\n')
    for section in js:
        out.write("\n")
        out.write("class TestApi%s\n" % (namify( section['name'])) )
        out.write("{\n")
        out.write("    private:\n")
        out.write("    QQueue<QString>* _queue;\n")
        out.write("\n")
        out.write("    public:\n")
        out.write("    TestApi%s( QQueue<QString>* queue );\n" % namify( section['name']) )
        out.write("\n")
        out.write("    void resetTestCallbacks();\n")

        for ep in section['endpoints']:
            out.write("\n")

            # write out the testing callback args the user can overload
            cb_args = []
            cb_args.append( "std::function<void (%s&)>" % ep['resp'] )
            cb_args.append( "std::function<void (%s&, bool)>" % ep['err'] )
            if len( ep['args'] ) > 0:
                args = [tTot(x).split(' ')[0] for x in ep['args']]
                out.write( "    std::function<void (%s, %s)> %sCallback = nullptr;\n" % (', '.join( args ), ', '.join(cb_args), ep['name']))
            else:
                out.write( "    std::function<void (%s)> %sCallback = nullptr;\n" % (', '.join(cb_args), ep['name']))

            #Short form template
            if len(ep['args']) > 0:
                args = [tTot(x) for x in ep['args']]
                out.write("    void %s( %s,\n" % (ep['name'], ', '.join(args)))
            else:
                out.write("    void %s(\n" % (ep['name']))
            out.write("             std::function<void (%s&)> success = nullptr,\n" % ep['resp'])
            out.write("             std::function<void (%s&, bool)> failed = nullptr );\n" % ep['err'])

        out.write("};\n")

    # Create the header for the main api object
    out.write("\n")
    out.write("class ApiInterface : public QObject\n")
    out.write("{\n")
    out.write("    Q_OBJECT\n")
    out.write("\n")
    out.write("    private:\n")
    out.write("    bool _networkOnline = false;\n")
    out.write("\n")
    out.write("    public:\n")
    out.write("\n")
    out.write("    QQueue<QString> Actions;\n")
    out.write("\n")
    out.write("    static const int MAJOR = 1;\n")
    out.write("    static const int MINOR = 0;\n")
    out.write("\n")
    out.write("    ApiInterface( Mailbox* mailbox );\n")
    out.write("\n")
    out.write("    void resetTestCallbacks();\n")
    out.write("\n")
    out.write("    bool isOnline();\n")
    out.write("\n")
    for section in js:
        out.write("    TestApi%s %s;\n" % (namify( section['name']), namify( section['name'])))
    out.write("\n")
    out.write("    public slots:\n")
    out.write("\n")
    out.write("    void onNetworkStatusChanged( bool online );\n")
    out.write("};\n")
    out.write("\n")
    out.write("#endif\n")
    out.close()


    ### Write out test_api.cpp

    out = open(dir+"Net/test_api.cpp", "w")
    out.write("// Generated file.\n")
    out.write("// Edit CodeGenerators/api.py, then run ./export_api.py ..\n\n")
    out.write("#ifdef API_PICKER\n")
    out.write('#include <functional>\n')
    out.write('#include <Net/test_api.h>\n')
    out.write('#include <Json/json_struct.h>\n')
    out.write('#include <Util/api_util.h>\n')
    out.write('#include <QtTest>\n')
    for section in js:
        out.write("\n")
        out.write("TestApi%s::TestApi%s( QQueue<QString>* queue) : _queue( queue ) {}\n" % (namify( section['name']), namify( section['name'])) )
        out.write("\n")
        out.write("void TestApi%s::resetTestCallbacks()\n" % (namify( section['name'])))
        out.write("{\n")
        for ep in section['endpoints']:
            out.write( "    %sCallback = nullptr;\n" % (ep['name']) )
        out.write("}\n")


        for ep in section['endpoints']:
            out.write("\n")

            if len(ep['args']) > 0:
                args = [tTot(x) for x in ep['args']]
                out.write("void TestApi%s::%s( %s,\n" % (namify( section['name']), ep['name'], ', '.join(args)))
            else:
                out.write("void TestApi%s::%s(\n" % (namify( section['name']), ep['name']))

            out.write("                std::function<void (%s&)> success,\n" % ep['resp'])
            out.write("                std::function<void (%s&, bool)> failed )\n" % ep['err'])
            out.write("{\n")

            out.write('    _queue->enqueue("%s->%s");\n' % (namify(section['name']), ep['name']) )
            out.write("\n")

            out.write( "    if ( %sCallback != nullptr )\n" % (ep['name']) )
            if len( ep['args'] ) > 0:
                args = [tTot(x).split(' ')[1] for x in ep['args']]
                out.write( "        %sCallback( %s, success, failed );\n" % (ep['name'], ', '.join( args )) )
            else:
                out.write( "        %sCallback( success, failed );\n" % (ep['name']) )
            out.write('    else\n')
            out.write('        QVERIFY2(false, "No callback set for %s->%s");\n' % (namify(section["name"]), ep['name']))
            out.write("}\n")

    # Build out my top level api call object
    out.write("\n")
    out.write("ApiInterface::ApiInterface( Mailbox* mailbox ) : \n")
    out.write('%s\n' % (',\n'.join(["    %s( &Actions )" % namify( x['name']) for x in js])))
    out.write("{\n")
    out.write("    QObject::connect( mailbox, &Mailbox::networkStatusChanged, this, &ApiInterface::onNetworkStatusChanged );\n")
    out.write("}\n")

    out.write("\n")
    out.write("void ApiInterface::resetTestCallbacks()\n")
    out.write("{\n")
    for section in js:
        out.write("    %s.resetTestCallbacks();\n" % (namify( section['name']))) 
    out.write("}\n")

    out.write("\n")
    out.write("bool ApiInterface::isOnline()\n")
    out.write("{\n")
    out.write("    return _networkOnline;\n")
    out.write("}\n")

    out.write("\n")
    out.write("void ApiInterface::onNetworkStatusChanged( bool online )\n")
    out.write("{\n")
    out.write("    _networkOnline = online;\n")
    out.write("}\n")
    out.write("#endif\n")

    out.close()


    # Write out the inclusion info
    out = open(dir+"Net/api.h", "w")
    out.write('''// Generated.  Please edit api.py to change this file.
#ifdef TEST_API
    #include "test_api.h"
#else
    #include "net_api.h"
#endif
    ''')
    out.close()

    out = open(dir+"Net/api.cpp", "w")
    out.write('''// Generated.  Please edit api.py to change this file.
#define API_PICKER
#ifdef TEST_API
    #include "test_api.cpp"
#else
    #include "net_api.cpp"
#endif
    ''')
    out.close()


# Ensure we have enough args
if len(sys.argv) < 2:
    print("Usage ./%s output_dir" % sys.argv[0])
    exit(0)

handle( api_data(), sys.argv[1] )
#handle( sys.argv[1], sys.argv[2] )

