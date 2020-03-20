#!/usr/bin/python3

import json, time, re, sys, os
from mailbox import mailbox_data


def type_to_variant( btype ):
    if re.search(r"^list", btype) is not None:
        return "QVariantList"
    if re.search(r"^str", btype) is not None:
        return "QString"
    if re.search(r"^float", btype) is not None:
        return "double"
    if re.search(r"^long", btype) is not None:
        return "qint64"
    if re.search(r"^int", btype) is not None:
        return "int"
    if re.search(r"^bool", btype) is not None:
        return "bool"
    if re.search(r"^variant", btype) is not None:
        return "QJSValue"

    return "QVariant"


def type_to_jsvalue( btype ):
    if re.search(r"^list", btype) is not None:
        return "QJSValue"
    if re.search(r"^str", btype) is not None:
        return "QString"
    if re.search(r"^float", btype) is not None:
        return "double"
    if re.search(r"^long", btype) is not None:
        return "qint64"
    if re.search(r"^int", btype) is not None:
        return "int"
    if re.search(r"^bool", btype) is not None:
        return "bool"

    return "QJSValue"


def qml_obj_converter( btype, var ):
    if re.search(r"^list", btype) is not None or \
       re.search(r"^str", btype) is not None or \
       re.search(r"^float", btype) is not None or \
       re.search(r"^long", btype) is not None or \
       re.search(r"^int", btype) is not None or \
       re.search(r"^bool", btype) is not None or \
       re.search(r"^variant", btype) is not None:
        return var

    return "%s( %s ).exportValue()" % (btype, var)


def remote_obj_converter( btype, var, emit ):
    if re.search(r"^str", btype) is not None or \
       re.search(r"^float", btype) is not None or \
       re.search(r"^long", btype) is not None or \
       re.search(r"^int", btype) is not None or \
       re.search(r"^bool", btype) is not None or \
       re.search(r"^variant", btype) is not None:
        return (var, var, None)

    match = re.search(r'^list<([^>]+)>', btype)
    if match is not None:
        prep  = "        QVariantList %s_conv;\n" % (var)
        prep += "        for ( auto& item : %s )\n" % (var)
        prep += '        {\n'
        prep += '            %s_conv.append( item.toJson() );\n' % (var)
        prep += '        }\n'
        return (var, "QJsonArray::fromVariantList( %s_conv )" % var, prep)

    if emit == "qml":
        return (var, "%s( %s ).exportValue()" % (btype, var), None)
    else:
        return (var, "%s.toJson()" % var, None)


def map_json_converter( emit, btype, var, name ):
    if re.search(r"^str", btype) is not None:
        return ('%s["%s"].toString()' % (var, name), None)
    if re.search(r"^float", btype) is not None:
        return ('%s["%s"].toDouble()' % (var, name), None)
    if re.search(r"^long", btype) is not None:
        return ('static_cast<qint64>( %s["%s"].toDouble() )' % (var, name), None)
    if re.search(r"^int", btype) is not None:
        return ('%s["%s"].toInt()' % (var, name), None)
    if re.search(r"^bool", btype) is not None:
        return ('%s["%s"].toBool()' % (var, name), None)

    match = re.search(r'^list<([^>]+)>', btype)
    if match is not None:
        btype = match[1]
        prep  = '                    auto %s_ary = %s["%s"].toArray();\n' % (name, var, name)
        prep += '                    QList<%s> %s_conv;\n' % (btype, name)
        if emit == "cpp":
            prep += '                    for ( auto i = 0; i < %s_ary.count(); i++ )\n' % (name)
            prep += '                    {\n'
            prep += '                        auto pin = %s_ary.at(i).toObject();\n' % (name)
            prep += '                        %s_conv.append( %s::fromJson( &pin ));\n' % (name, btype)
            prep += '                    }\n'
        else:
            prep += '                    for ( auto i = 0; i < %s_ary.count(); i++ )\n'
            prep += '                    {\n'
            prep += '                        auto pin = %s_ary.at(i).toObject();\n' % (name)
            prep += '                        %s_conv.append( %s::fromJson( &pin ).exportQJSValue() );\n' % (name, btype)
            prep += '                    }\n'
        return ("%s_conv" % name, prep)

    if emit == "cpp":
        prep  = '                    auto __%s = %s["%s"].toObject();\n' % (name, var, name)
        return ('%s::fromJson( &__%s )' % (btype, name), prep)
        #return ('%s( %s["%s"].toObject() )' % (btype, var, name), None)
    else:
        return ('%s( %s["%s"].toObject() ).exportQJSValue()' % (btype, var, name), None)


def type_to_type( btype ):
    btype = re.sub(r"^str", "QString", btype)
    btype = re.sub(r"^float", "double", btype)
    btype = re.sub(r"^list", "QList", btype)
    btype = re.sub(r"^long", "qint64", btype)
    btype = re.sub(r"<str>", "<QString>", btype)
    btype = re.sub(r"<int>", "<int>", btype)
    btype = re.sub(r"<float>", "<double>", btype)
    btype = re.sub(r"<long>", "<qint64>", btype)
    return btype


def cpp_to_qml( btype, name ):
    # Are we a list!!?!?!, we're going to recurse then
    match = re.search(r'^list<([^>]+)>', btype)
    if match is not None:
        entry = "entry_%s" % name
        msg  = "        QList<QVariant> ary_%s;\n" % name
        msg += "        for ( auto %s : %s )\n" % (entry, name)
        msg += "            ary_%s.push_back( %s );\n" % (name, cpp_to_qml( match[1], entry)[0])
        return ("ary_%s" % name, msg)

    #Base type, just output the name
    if re.search(r'^str', btype) is not None or \
       re.search(r'^int', btype) is not None or \
       re.search(r'^bool', btype) is not None or \
       re.search(r'^float', btype) is not None or \
       re.search(r'^long', btype) is not None:
        return "%s" % name, None
    else:
        # Whatever else it is, it needs to handle exportValue();
        return 'QVariant( %s.toJson() )' % (name), None


def qml_to_cpp( btype, name ):
    # Are we a list!!?!?!, we're going to recurse then
    match = re.search(r'^list<([^>]+)>', btype)
    if match is not None:
        # entry = "%s.property(i)" % name
        msg  = "        QList<%s> ary_%s;\n" % (type_to_type(match[1]), name)
        msg += '        auto count_%s = static_cast<quint32>( %s.property("length").toInt());\n' % (name, name)
        msg += '        for (quint32 i = 0; i < count_%s; i++ )\n' % name
        msg += '        {\n'
        msg += "            auto pin = %s.property(i);\n" % name
        msg += "            ary_%s.push_back( %s );\n" % (name, qml_to_cpp( match[1], "pin")[0])
        msg += '        }\n'
        return ("ary_%s" % name, msg)

    #Base type, just output the name
    if re.search(r'^str', btype) is not None or \
       re.search(r'^int', btype) is not None or \
       re.search(r'^bool', btype) is not None or \
       re.search(r'^float', btype) is not None or \
       re.search(r'^long', btype) is not None:
        return "%s" % name, None
    #elif re.search(r'^point', btype) is not None:
    #    return "%s.toPointF()" % name, ""
    else:
        # Whatever else it is, it needs to handle exportValue();
        return '%s::fromQJSValue( &%s )' % (btype, name), None


def debug_convert_arg( btype, name ):
    #Base type, just output the name
    if re.search(r'^str', btype) is not None:
        return "%s{%%s}" % name, "%s.toUtf8().data()" % name
    elif re.search(r'^int', btype) is not None:
        return "%s{%%d}" % name, name
    elif re.search(r'^bool', btype) is not None:
        return "%s{%%s}" % name, '(%s ? "true": "false")' % name
    elif re.search(r'^float', btype) is not None:
        return "%s{%%f}" % name, name
    elif re.search(r'^long', btype) is not None:
        return "%s{%%lld}" % name, name
    else:
        # Whatever else it is, it needs to handle exportValue();
        return "%s{%s}" % (name, btype), None


def call_debug( remote, args, func_name ):
    # Setup the conversion logic
    signal_args = []
    signal_values = []
    for arg in args:
        s = arg.split(' ')
        a, v = debug_convert_arg( s[0], s[1] )
        signal_args.append(a)
        if v is not None:
            signal_values.append(v)

    if remote:
        if len(signal_values) > 0:
            return 'qDebug("%%sMAILBOX -> %s( %s )", (%s ? "": "TCP "), %s)' % (func_name, ', '.join(signal_args), remote, ', '.join(signal_values))
        else:
            return 'qDebug("%%sMAILBOX -> %s( %s )", (%s ? "": "TCP "))' % (func_name, ', '.join(signal_args), remote)
    else:
        if len(signal_values) > 0:
            return 'qDebug("MAILBOX -> %s( %s )", %s)' % (func_name, ', '.join(signal_args), ', '.join(signal_values))
        else:
            return 'qDebug("MAILBOX -> %s( %s )")' % (func_name, ', '.join(signal_args))


def capitalize( val ):
    return val[0].capitalize() + val[1:]


def emit_data( emit, args, name ):
    params = []
    for arg in args:
        s = arg.split(' ')

        if emit == "cpp":
            params.append('%s %s' % (type_to_type(s[0]), s[1]))
        elif emit == "qml":
            params.append('%s %s' % (type_to_jsvalue(s[0]), s[1]))

    return ("emit%s" % capitalize( name ), ', '.join(params) )


def signal_data( signal, args, name ):
    params = []
    for arg in args:
        s = arg.split(' ')

        if signal == "cpp":
            params.append('%s %s' % (type_to_type(s[0]), s[1]))
        elif signal == "qml":
            params.append('%s %s' % (type_to_variant(s[0]), s[1]))

    return ( "%s" % name, ', '.join(params))


def call_signal( signal, emit, args, func_name ):
    # Same same, easy, just send stuff out
    if signal == emit:
        params = []
        for arg in args:
            s = arg.split(' ')
            if signal == "qml":
                params.append(qml_obj_converter(s[0], s[1]))
            else:
                params.append(s[1])
        return (func_name, ', '.join(params), None)

    # Setup the conversion logic
    signal_args = []
    signal_prep = []
    for arg in args:
        s = arg.split(' ')
        v, p = cpp_to_qml(s[0], s[1]) if signal == 'qml' else qml_to_cpp(s[0], s[1])
        signal_args.append(v)
        if p is not None:
            signal_prep.append(p)
    return (func_name, ', '.join(signal_args), '\n'.join(signal_prep))


def call_remote( emit, args, func_name ):
    # Same same, easy, just send stuff out
    params = []
    call_prep = []
    for arg in args:
        s = arg.split(' ')
        name, conv, prep = remote_obj_converter(s[0], s[1], emit)
        params.append((name, conv))
        if prep is not None:
            call_prep.append( prep )

    if len(call_prep) > 0:
        return (func_name, params, "".join(call_prep))
    else:
        return (func_name, params, None)


def handle( js, output_dir ):
    #js = json.loads( " ".join(open( schema ).readlines()) )
    dir = output_dir + "/"

    for mode in ('cpp', 'qml'):
        # Open the file
        filename = "mailbox" if mode == "cpp" else "mailbox_qml"
        out = open("%sShared/%s.h" % (dir, filename), "w")

        # Setup the header varaibles
        pound_def = ""
        klass_name = "Mailbox"
        klass_sibling = "MailboxQml"
        if mode == "qml":
            pound_def = "_QML"
            klass_name = "MailboxQml"
            klass_sibling = "Mailbox"

        # Write out the header
        out.write('''// Generated file.
// Edit CodeGenerators/mailbox.py, then run ./export_mailbox.py ..

#ifndef MAILBOX%s_H
#define MAILBOX%s_H

#include <Json/json_struct.h>
#include <Net/tcp_manager.h>
#include <Debug/debug.h>

#include <QJSValue>
#include <QObject>
#include <QVariantList>
#include <QTcpSocket>

class %s;

class %s : public QObject
{
    Q_OBJECT

    public:
    static const int MAJOR = 1;
    static const int MINOR = 0;
    
    //Set to true for message logging
    bool Debug = false;
    
    private:
    %s* _sibling = nullptr;
    QJSEngine* _engine = nullptr;

    public:
    explicit %s( QObject *parent = nullptr);
    
    void loadSibling( %s* sibling );
    
    void loadEngine( QJSEngine* engine );
   
''' % (pound_def, pound_def, klass_sibling, klass_name, klass_sibling, klass_name, klass_sibling))

        # The "cpp" mailbox handles the TCP socket
        if mode == "cpp":
            out.write('''    private:
    TcpManager _tcpMang;
    
    public:
    bool isRemoteValid();
    bool connectRemote( bool single = false );
    bool listenRemote();
    bool closeRemote();
    
    private slots:
    
''')

        # Private methods to actually do the work
        out.write("    private:\n")
        for section in js:
            out.write("\n")
            out.write("    //*** Private %s\n\n" % section['section'])
            for endpoint in section['endpoints']:
                if mode == "cpp" and 'qml_only' in endpoint and endpoint['qml_only']:
                    continue
                func, args = emit_data( mode, ["bool allow_remote"] + endpoint['args'], endpoint['name'])
                out.write("    void _%s( %s );\n" % ( func, args ))
            out.write("\n")

        # The invokable
        out.write("    public slots:\n")
        for section in js:
            out.write("\n")
            out.write("    //*** %s\n\n" % section['section'])
            for endpoint in section['endpoints']:
                if mode == "cpp" and 'qml_only' in endpoint and endpoint['qml_only']:
                    continue
                func, args = emit_data( mode, endpoint['args'], endpoint['name'])
                out.write("    void %s( %s );\n" % ( func, args ))
            out.write("\n")

        if mode == 'cpp':
            out.write("\n")
            out.write("    private slots:\n")
            out.write("\n")
            out.write("    //*** Mailbox internal\n")
            out.write("\n")
            out.write("    void onConnectionChanged( bool connected );\n")

        # Signals
        out.write("\n")
        out.write("    signals:\n")
        if mode == 'cpp':
            out.write("\n")
            out.write("    //*** Mailbox internal\n")
            out.write("\n")
            out.write("    void remoteConnectionChanged( bool connected );\n")
        for section in js:
            out.write("\n")
            out.write("    //*** %s\n\n" % section['section'])
            for endpoint in section['endpoints']:
                if mode == "cpp" and 'qml_only' in endpoint and endpoint['qml_only']:
                    continue
                func, args = signal_data( mode, endpoint['args'], endpoint['name'] )
                out.write("    void %s( %s );\n" % ( func, args ) )

        out.write("};\n")
        out.write("\n")
        out.write("#endif\n")
        out.close()

        # Build out the register calls
        out = open("%sShared/%s.cpp" % (dir, filename), "w")
        out.write('''// Generated file.
// Edit CodeGenerators/mailbox.py, then run ./export_mailbox.py ..

#include "mailbox.h"
#include "mailbox_qml.h"
#include <QJsonDocument>
#include <QTimer>
#include <Debug/debug.h>
        
%s::%s( QObject *parent) : 
    QObject(parent)
''' % (klass_name, klass_name))

        if mode == "qml":
            out.write('{}\n')
        else:
            out.write( '''{
    QObject::connect( &_tcpMang, &TcpManager::connectionChanged,
                      this, &Mailbox::onConnectionChanged );
            
    //Read data
    _tcpMang.Callback = [&](const char* buffer, int len )
    {
        DebugDuration()
        auto&& data = QByteArray( buffer, len );
        QJsonParseError err;
        auto&& doc = QJsonDocument::fromJson( data, &err );
        if ( err.error != QJsonParseError::NoError )
        {
            R_FAILED("Error parsing socket data: %%1", err.errorString().toUtf8().data());
            qDebug("%s", data.data());
            return;
        }

        auto&& obj = doc.object();

        //Move this over to the main thread, not the socket thread we are currently running on
        QTimer::singleShot( 0, this, [this, obj]{
            auto func = obj.value("function_name").toString();

''' )

            # Body of the constructor
            for section in js:
                for endpoint in section['endpoints']:
                    if 'qml_only' in endpoint and endpoint['qml_only']:
                        continue

                    # Convert all the args
                    args = ['false']
                    preps = []
                    for arg in endpoint['args']:
                        s = arg.split( ' ' )
                        param, prep = map_json_converter( mode, s[0], "obj", s[1] )
                        args.append( param )
                        if prep is not None:
                            preps.append( prep )

                    out.write( '            if ( func == "%s" ) {\n' % (endpoint['name']) )
                    if len( preps ) > 0:
                        out.write( '%s\n' % "\n".join( preps ) )
                    out.write( '                _emit%s( %s );\n' % (
                    capitalize( endpoint['name'] ), ', '.join( args )) )
                    out.write( '            } else\n' )

            out.write( '                qDebug("Couldnt find matching function %s", func.toUtf8().data());\n' )
            out.write( '        });\n' )
            out.write( '    };\n' )
            out.write( '}\n' )

            out.write( '''
        
bool %s::isRemoteValid()
{
    return _tcpMang.isValid();
}

bool %s::connectRemote( bool single )
{
    return _tcpMang.connect( single );
}

bool %s::listenRemote()
{
    return _tcpMang.listen();
}

bool %s::closeRemote()
{
    return _tcpMang.close();
}
''' % (klass_name, klass_name, klass_name, klass_name) )


        ### End of constructor

        out.write( '''
void % s::loadEngine( QJSEngine* engine )
{
    _engine = engine;
}

void %s::loadSibling( %s* sibling )
{
    _sibling = sibling;
}

''' % (klass_name, klass_name, klass_sibling))

        if mode == "cpp":
            out.write('''
void Mailbox::onConnectionChanged(bool connected )
{
    if ( Debug ) qDebug("MAILBOX -> remoteConnectionChanged( connected{%s} )", (connected ? "true": "false"));
    
    emit remoteConnectionChanged(connected);
}
    ''')

            # Output the data
        for section in js:
            out.write("\n")
            out.write("//*** %s\n\n" % section['section'])
            for endpoint in section['endpoints']:
                # Write out the emit function
                if mode == "cpp":
                    # Skip any QML only stuff
                    if 'qml_only' in endpoint and endpoint['qml_only']:
                        continue

                    emit_func, emit_args = emit_data("cpp", ['bool allow_remote'] + endpoint['args'], endpoint['name'] )
                    out.write("void %s::_%s( %s )\n" % (klass_name, emit_func, emit_args) )
                    out.write("{\n")
                    out.write("    DebugDuration()\n")

                    # Warning surpression
                    if "remote" not in endpoint or not endpoint["remote"]:
                        out.write("    Q_UNUSED( allow_remote )\n\n")

                    # Debug logic only if we aren't listed as chatty
                    if "chatty" not in endpoint or not endpoint["chatty"]:
                        out.write('    if ( Debug ) %s;\n\n' % call_debug( "allow_remote", endpoint['args'], endpoint['name'] ))

                    # Go through and implement targets
                    signal_func, signal_args, signal_prep = call_signal( "qml", "cpp", endpoint['args'], endpoint['name'] )
                    out.write("    if ( _sibling != nullptr ) {\n")
                    if signal_prep is not None:
                        out.write(signal_prep)
                        out.write("\n")
                    out.write("        emit _sibling->%s( %s );\n" % (signal_func, signal_args ))
                    out.write("    }\n")
                    #out.write("    else\n")
                    #out.write('        qDebug("No sibling loaded: %s()");\n' % emit_func)

                    # CPP  output
                    signal_func, signal_args, signal_prep = call_signal( "cpp", "cpp", endpoint['args'], endpoint['name'] )
                    out.write("    emit this->%s( %s );\n" % (signal_func, signal_args ))

                    # Send to remote?
                    if "remote" in endpoint and endpoint["remote"]:
                        signal_func, signal_args, signal_prep = call_remote( "cpp", endpoint['args'], endpoint['name'] )
                        out.write("\n    if ( allow_remote && isRemoteValid() ) {\n")
                        if signal_prep is not None:
                            out.write(signal_prep)
                            out.write("\n")
                        out.write("        QJsonObject msg;\n")
                        out.write('        msg.insert( "function_name", "%s" );\n' % signal_func)

                        for args in signal_args:
                            out.write('        msg.insert( "%s", %s );\n' % (args[0], args[1]))
                        out.write("\n        QJsonDocument json_doc( msg );\n")
                        out.write("        auto raw_msg = json_doc.toJson();\n")
                        out.write("        _tcpMang.write( raw_msg );\n")
                        out.write("    }\n")

                    out.write("}\n")

                    # Write out the paried private method for this call
                    emit_func, emit_args = emit_data("cpp", endpoint['args'], endpoint['name'] )
                    emit_arg_names = ', '.join( [x.split(' ')[-1] for x in endpoint['args']])
                    out.write("void %s::%s( %s )\n" % (klass_name, emit_func, emit_args) )
                    if emit_arg_names != "":
                        out.write("{ _%s( true, %s ); }\n\n" % (emit_func, emit_arg_names) )
                    else:
                        out.write("{ _%s( true ); }\n\n" % (emit_func) )


                else: # QML
                    emit_func, emit_args = emit_data("qml", endpoint['args'], endpoint['name'] )
                    out.write("void %s::%s( %s )\n{\n" % (klass_name, emit_func, emit_args) )
                    out.write("    DebugDuration()\n")

                    if 'qml_only' in endpoint and endpoint['qml_only']:
                        # Debug logic only if we aren't listed as chatty
                        if "chatty" not in endpoint or not endpoint["chatty"]:
                            out.write('    if ( Debug ) %s;\n\n' % call_debug( None, endpoint['args'], endpoint['name'] ))

                        signal_func, signal_args, signal_prep = call_signal( "qml", "qml", endpoint['args'], endpoint['name'] )
                        out.write("    emit this->%s( %s );\n" % (signal_func, signal_args ))
                    else:
                        signal_func, signal_args, signal_prep = call_signal( "cpp", "qml", endpoint['args'], endpoint['name'] )
                        out.write("    if ( _sibling != nullptr ) {\n")
                        if signal_prep is not None:
                            out.write(signal_prep)
                            out.write("\n")
                        out.write("        //Pass to CPP mailbox to actually deliver the message.\n")
                        out.write("        _sibling->%s( %s );\n" % (emit_func, signal_args ))
                        out.write("    }\n")
                        out.write("    else\n")
                        out.write('        qDebug("No sibling loaded: %s()");\n' % emit_func)
                    out.write("}\n\n")



        out.close()

# Ensure we have enough args
if len(sys.argv) < 2:
    print("Usage ./%s output_dir" % sys.argv[0])
    exit(0)

handle( mailbox_data(), sys.argv[1] )
#handle( sys.argv[1], sys.argv[2] )

