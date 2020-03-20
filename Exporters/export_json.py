#!/usr/bin/python3

import re, sys, os
from json import struct_data


def parse_type( btype ):
    match = re.match(r'^list<(.+)>', btype)
    if match is not None:
        recurse = parse_type( match[1] )
        return ('QList<%s>' % recurse[0], recurse[1], match[1], None)

    if btype == "str":
        return ("QString", True, None, None)
    elif btype == "float":
        return ("double", True, None, "0.0")
    elif btype == "int":
        return ("int", True, None, "0")
    elif btype == "long":
        return ("qint64", True, None, "0")
    elif btype == "bool":
        return ("bool", True, None, "false")
    else:
        return (btype, False, None, None)


def primitive_value( btype, input ):
    if btype == "str":
        return '%s.toString()' % input
    elif btype == "float":
        return '%s.toDouble()' % input
    elif btype == "int":
        return '%s.toInt()' % input
    elif btype == "long":
        return 'static_cast<qint64>( %s.toDouble() )' % input
    elif btype == "bool":
        return '%s.toBool()' % input
    else:
        return '%s::fromJson( %s )' % (btype, input)


def primitive_qjs( btype, input ):
        if btype == "str":
            return '%s.toString()' % input
        elif btype == "float":
            return '%s.toNumber()' % input
        elif btype == "int":
            return '%s.toInt()' % input
        elif btype == "long":
            return 'static_cast<qint64>( %s.toNumber() )' % input
        elif btype == "bool":
            return '%s.toBool()' % input
        else:
            return None


def handy( struct ):
    fields = []
    for field in struct['fields']:
        info = field.split(' ')
        parse = parse_type( info[0])
        fields.append( {'cpp': parse[0],
                        'primitive': parse[1],
                        'array': parse[2],
                        'init': parse[3],
                        'py': info[0],
                        'name': info[1]
                        } )

    return (struct['name'], fields)


def handle( js, output_dir ):
    dir = output_dir + "/"

    out = open(dir+"Json/json_struct.h", "w")
    out.write('''// Generated file.
// Edit Scripts/json.py, then run ./export_struct.py ..

#ifndef JSON_STRUCT_H
#define JSON_STRUCT_H

#include <QList>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonValue>
#include <QJSValue>
#include "json_struct_helper.h"
''')

    # Output the api
    for struct in js:
        klass, fields = handy( struct )

        out.write("\n")
        out.write("class %s\n" % klass )
        out.write("{\n")
        out.write("    JSON_STRUCT_HELPER( %s )\n" % klass )
        out.write("\n")
        for field in fields:
            if field['init'] is not None:
                out.write("    %s %s = %s;\n" % (field['cpp'], field['name'], field['init']) )
            else:
                out.write("    %s %s;\n" % (field['cpp'], field['name']))
        out.write("};\n")

    out.write("\n")
    out.write("void apiStructRegister();\n")
    out.write("\n")
    out.write("#endif\n")
    out.close()


    ### CPP output

    # Build out the register calls
    out = open(dir+"Json/json_struct.cpp", "w")
    out.write('// Generated file.\n')
    out.write('// Edit Scripts/json.py, then run ./export_struct.py ..\n\n')
    out.write('#include <Json/json_struct.h>\n')
    out.write('#include <Util/api_util.h>\n')

    # Output the api
    for struct in js:
        klass, fields = handy( struct )
        out.write("\n")

        ## fromJson()
        out.write("%s %s::fromJson( QJsonObject&& obj, bool* successful )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    return fromJson( &obj, successful );\n")
        out.write("}\n")

        ## fromJson()
        out.write("%s %s::fromJson( QJsonObject* obj, bool* successful )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    %s result;\n" % klass)
        out.write("    int hits = 0;\n")
        out.write("\n")
        if len(fields) <= 0:
            out.write( "    Q_UNUSED(obj)\n" )

        for field in fields:
            # Are we a primitive
            if field['primitive']:
                # Deal with an Array
                if field['array']:
                    out.write('    if (obj->contains("%s") )\n' % field['name'])
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& ary = (*obj)["%s"].toArray();\n' % field['name'])
                    out.write('        for (int i = 0; i < ary.count(); i++ )\n')
                    out.write('            result.%s.append( %s );\n' % (field['name'], primitive_value(field['array'], 'ary[i]')))
                    out.write('    }\n')
                else:
                    data = primitive_value( field['py'], '(*obj)["%s"]' % (field['name']))
                    out.write('    if ( obj->contains( "%s" ) )\n' % (field['name']))
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        result.%s = %s;\n' % (field['name'], data))
                    out.write('    }\n')

            # This isn't primitive
            else:
                # Deal with an array
                if field['array']:
                    out.write('    if (obj->contains("%s") )\n' % field['name'])
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& ary = (*obj)["%s"].toArray();\n' % field['name'])
                    out.write('        for (int i = 0; i < ary.count(); i++ )\n')
                    out.write('        {\n')
                    out.write('            auto&& pin = ary[i].toObject();\n')
                    out.write('            auto&& info = %s::fromJson( &pin );\n' % field['array'])
                    out.write('            result.%s.append(info);\n' % field['name'])
                    out.write('        }\n')
                    out.write('    }\n')
                else:
                    out.write('    if ( obj->contains( "%s" ) )\n' % field['name'] )
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& pin = (*obj)["%s"].toObject();\n' % field['name'])
                    out.write('        result.%s = %s::fromJson( &pin );\n' % (field['name'], field['cpp']))
                    out.write('    }\n')

        out.write("\n")
        out.write("    if ( successful != nullptr ) *successful = (hits == %d);\n" % len(fields))
        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")
        out.write("\n")

        ## fromQJSValue()
        out.write("%s %s::fromQJSValue( QJSValue* obj, bool* successful )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    %s result;\n" % klass)
        out.write("    int hits = 0;\n")
        out.write("\n")
        if len(fields) <= 0:
            out.write( "    Q_UNUSED(obj)\n" )

        for field in fields:
            # Are we a primitive
            if field['primitive']:
                # Deal with an Array
                if field['array']:
                    out.write('    if (obj->hasProperty("%s") )\n' % field['name'])
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& ary = obj->property("%s");\n' % field['name'])
                    out.write('        auto count = static_cast<quint32>( ary.property("length").toInt());\n')
                    out.write('        for (quint32 i = 0; i < count; i++ )\n')
                    out.write('            result.%s.append( %s );\n' % (field['name'], primitive_qjs(field['array'], 'ary.property(i)')))
                    out.write('    }\n')
                else:
                    data = primitive_qjs( field['py'], 'obj->property("%s")' % (field['name']))
                    out.write('    if ( obj->hasProperty( "%s" ) )\n' % field['name'])
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        result.%s = %s;\n' % (field['name'], data))
                    out.write('    }\n')

            # This isn't primitive
            else:
                # Deal with an array
                if field['array']:
                    out.write('    if (obj->hasProperty("%s") )\n' % field['name'])
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& ary = obj->property("%s");\n' % field['name'])
                    out.write('        auto count = static_cast<quint32>( ary.property("length").toInt());\n')
                    out.write('        for (quint32 i = 0; i < count; i++ )\n')
                    out.write('        {\n')
                    out.write('            auto&& pin = ary.property(i);\n')
                    out.write('            auto&& info = %s::fromQJSValue( &pin );\n' % field['array'])
                    out.write('            result.%s.append(info);\n' % field['name'])
                    out.write('        }\n')
                    out.write('    }\n')
                else:
                    out.write('    if ( obj->hasProperty( "%s" ) )\n' % field['name'] )
                    out.write('    {\n')
                    out.write('        hits++;\n')
                    out.write('        auto&& pin = obj->property("%s");\n' % field['name'])
                    out.write('        result.%s = %s::fromQJSValue( &pin );\n' % (field['name'], field['cpp']))
                    out.write('    }\n')

        out.write("\n")
        out.write("    if ( successful != nullptr ) *successful = (hits == %d);\n" % len(fields))
        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")
        out.write("\n")

        ## fromJsonList
        out.write("QList<%s> %s::fromJsonList( QList<QJsonObject>&& ary, bool* successful )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    QList<%s> result;\n" % klass)
        out.write("    bool succ = true;\n")
        out.write("\n")
        out.write("    for ( auto& entry : ary ) {\n")
        out.write("        bool tmp = false;\n")
        out.write("        result.append( %s::fromJson( &entry, &tmp ) );\n" % klass)
        out.write("        succ &= tmp;\n")
        out.write("    }\n")
        out.write("\n")
        out.write("    if ( successful != nullptr ) *successful = succ;\n")
        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")
        out.write("\n")

        ## fromJsonList
        out.write("QList<%s> %s::fromJsonList( QList<QJsonObject>* ary, bool* successful )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    QList<%s> result;\n" % klass)
        out.write("    bool succ = true;\n")
        out.write("\n")
        out.write("    for ( auto& entry : *ary ) {\n")
        out.write("        bool tmp = false;\n")
        out.write("        result.append( %s::fromJson( &entry, &tmp ) );\n" % klass)
        out.write("        succ &= tmp;\n")
        out.write("    }\n")
        out.write("\n")
        out.write("    if ( successful != nullptr ) *successful = succ;\n")
        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")
        out.write("\n")

        ## toArray
        out.write("QJsonArray %s::toArray( QList<%s>* ary )\n" % (klass, klass) )
        out.write("{\n")
        out.write("    QVariantList result;\n")
        out.write("\n")
        out.write("    for ( auto& entry : *ary )\n")
        out.write("        result.append( entry.toJson() );\n")
        out.write("\n")
        out.write("    return QJsonArray::fromVariantList( result );\n")
        out.write("}\n")
        out.write("\n")

        ### toQJSValue()
        #out.write("QJSValue %s::toQJSValue( QJSEngine* engine )\n" % klass )
        #out.write("{\n")
        #out.write("    QJSValue result;\n")
        #out.write("\n")
        #engine_used = False
        #for field in fields:
        #    # Are we a primitive
        #    if field['primitive']:
        #        # Deal with an Array
        #        if field['array']:
        #            engine_used = True
        #            out.write('    {\n')
        #            out.write('        auto&& ary = QVariantList();\n')
        #            out.write('        for (auto& item : %s )\n' % field['name'])
        #            out.write('            ary.append( item );\n')
        #            out.write('        result.setProperty( "%s", convertToQJSValue( engine, QJsonValue( QJsonArray::fromVariantList( ary))));\n' % field['name'])
        #            out.write('    }\n')
        #        else:
        #            if field['py'] != 'long':
        #                out.write('    result.setProperty( "%s", %s );\n' % (field['name'], field['name']))
        #            else:
        #                out.write('    result.setProperty( "%s", static_cast<double>(%s) );\n' % (field['name'], field['name']))

        #    # This isn't primitive
        #    else:
        #        # Deal with an array
        #        if field['array']:
        #            engine_used = True
        #            out.write('    {\n')
        #            out.write('        auto&& ary = QVariantList();\n')
        #            out.write('        for (auto& item : %s )\n' % field['name'])
        #            out.write('            ary.append( item.toJson() );\n')
        #            out.write('        result.setProperty( "%s", convertToQJSValue( engine, QJsonValue( QJsonArray::fromVariantList( ary))));\n' % field['name'])
        #            out.write('    }\n')
        #        else:
        #            engine_unused = True
        #            out.write('    result.setProperty( "%s", convertToQJSValue( engine, QJsonValue( %s.toJson())));\n' % (field['name'], field['name']))

        #out.write("\n")
        #if not engine_used:
        #    out.write("    Q_UNUSED(engine)\n")
        #    out.write("\n")
        #out.write("    return result;\n")
        #out.write("}\n")

        ## toJson()
        out.write("QJsonObject %s::toJson()\n" % klass )
        out.write("{\n")
        out.write("    QJsonObject result;\n")
        out.write("\n")
        for field in fields:
            # Are we a primitive
            if field['primitive']:
                # Deal with an Array
                if field['array']:
                    out.write('    {\n')
                    out.write('        auto&& ary = QVariantList();\n')
                    out.write('        for (auto& item : %s )\n' % field['name'])
                    out.write('            ary.append( item );\n')
                    out.write('        result.insert( "%s", QJsonArray::fromVariantList( ary ) );\n' % field['name'])
                    out.write('    }\n')
                else:
                    out.write('    result.insert( "%s", QJsonValue(%s) );\n' % (field['name'], field['name']))

            # This isn't primitive
            else:
                # Deal with an array
                if field['array']:
                    out.write('    {\n')
                    out.write('        auto&& ary = QVariantList();\n')
                    out.write('        for (auto& item : %s )\n' % field['name'])
                    out.write('            ary.append( item.toJson() );\n')
                    out.write('        result.insert( "%s", QJsonArray::fromVariantList( ary ) );\n' % field['name'])
                    out.write('    }\n')
                else:
                    out.write('    result.insert( "%s", %s.toJson() );\n' % (field['name'], field['name']))

        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")

        ## toJson()
        out.write("QJsonObject %s::describeObject()\n" % klass )
        out.write("{\n")
        out.write("    QJsonObject result;\n")
        out.write("\n")
        for field in fields:
            # Are we a primitive
            if field['primitive']:
                # Deal with an Array
                if field['array']:
                    out.write('    {\n')
                    out.write('        auto&& ary = QVariantList();\n')
                    out.write('        ary.append( QJsonValue("%s") );\n' % field['array'])
                    out.write('        result.insert( "%s", QJsonArray::fromVariantList( ary ) );\n' % field['name'])
                    out.write('    }\n')
                else:
                    out.write('    result.insert( "%s", QJsonValue("%s") );\n' % (field['name'], field['cpp']))

            # This isn't primitive
            else:
                # Deal with an array
                if field['array']:
                    out.write('    {\n')
                    out.write('        auto&& ary = QVariantList();\n')
                    out.write('        ary.append( %s().describeObject() );\n' % field['array'])
                    out.write('        result.insert( "%s", QJsonArray::fromVariantList( ary ) );\n' % field['name'])
                    out.write('    }\n')
                else:
                    out.write('    result.insert( "%s", %s.describeObject() );\n' % (field['name'], field['name']))

        out.write("\n")
        out.write("    return result;\n")
        out.write("}\n")

    out.write("\n")
    out.write("void apiStructRegister()\n")
    out.write("{\n")
    for struct in js:
        out.write('    qRegisterMetaType<%s>( "%s" );\n' % (struct['name'], struct['name']))
        out.write('    qRegisterMetaType<QList<%s>>( "QList<%s>" );\n' % (struct['name'], struct['name']))
    out.write("}\n\n")
    #for struct in js: out.write("%s::~%s() {}\n" % (struct['name'], struct['name']))
    out.close()


# Ensure we have enough args
if len(sys.argv) < 2:
    print("Usage ./%s output_dir" % sys.argv[0])
    exit(0)

handle( struct_data(), sys.argv[1] )

