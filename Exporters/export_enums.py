#!/usr/bin/python3

import re, sys, os
from enums import struct_data

def decap( s ):
    return s[:1].lower() + s[1:] if s else ''


def handle( js, output_dir ):
    dir = output_dir + "/"

    out = open(dir+"Enums/enums.h", "w")
    out.write('''// Generated file.
// Edit Enums/enums.py, then run ./export_enums.py ..

#ifndef ENUMS_H
#define ENUMS_H

#include <QString>
#include <QObject>
#include <QQmlContext>
''')

    # Output the api
    for struct in js:
        out.write("\n")
        out.write("namespace %s\n" % struct['name'] )
        out.write("{\n")
        out.write("    Q_NAMESPACE\n")
        out.write("\n")
        out.write("    enum _ {\n")
        for field in struct['fields']:
            out.write("        %s,\n" %  field)
        out.write("    };\n")
        out.write("    Q_ENUM_NS(_)\n")
        out.write("\n")
        out.write("    QString toStr( _ name );\n")
        out.write("    _ fromStr( QString name );\n")
        out.write("}\n")
        out.write("\n")
        out.write("typedef %s::_ %sEnum;\n" % (struct['name'], struct['name']))

    out.write("\n")
    out.write("class Enums : public QObject {\n")
    out.write("\n")
    out.write("    Q_OBJECT\n")
    out.write("\n")
    out.write("    public:\n")
    out.write("    static const int MAJOR = 1;\n")
    out.write("    static const int MINOR = 0;\n")
    out.write("\n")
    out.write("    private:\n")
    for struct in js:
        out.write("    %s::_ _%s;\n" % (struct['name'], decap( struct['name'] )))
    out.write("\n")
    out.write("    public:\n")
    out.write("    static void enumRegister();\n")
    for struct in js:
        out.write("\n")
        out.write("    Q_INVOKABLE int %sFromStr( QString str );\n" % (decap(struct['name'])))
        out.write("    Q_INVOKABLE QString %sToStr( int code );\n" % (decap(struct['name'])))
    out.write("};\n")
    out.write("\n")
    out.write("#endif\n")
    out.close()


    ### CPP output

    out = open(dir + "Enums/enums.cpp", "w")
    out.write('''// Generated file.
// Edit Enums/enums.py, then run ./export_enums.py ..

#include "enums.h"

#include <QQmlEngine>
''')

    # Output the api
    out.write("\n")
    out.write("void Enums::enumRegister()\n")
    out.write("{\n")
    for struct in js:
        out.write('    qmlRegisterUncreatableMetaObject( %s::staticMetaObject, "Radius", 1, 0, "%s", "%s" );\n' % (struct['name'], struct['name'], struct['desc']))
        out.write('    qRegisterMetaType<%sEnum>( "%s" );\n' % (struct['name'], struct['name']))
        out.write("\n")
    out.write("}\n")

    out.write("\n")
    for struct in js:
        out.write("\n")
        out.write("int Enums::%sFromStr( QString name )\n" % (decap(struct['name'])))
        out.write("{\n")
        out.write("    ")
        for field in struct['fields']:
            field = re.sub("[ ].*$", '', field)
            out.write('if ( name == "%s" )\n' % field)
            out.write('        return (int)%s::%s;\n' % (struct['name'], field))
            out.write('    else ')
        out.write("\n        return (int)%s::%s;\n" % (struct['name'], struct['fields'][0]))
        out.write("}\n")
        out.write("\n")

        out.write("QString Enums::%sToStr( int name )\n" % (decap(struct['name'])))
        out.write("{\n")
        out.write("    ")
        for field in struct['fields']:
            field = re.sub("[ ].*$", '', field)
            out.write('if ( name == (int)%s::%s )\n' % (struct['name'], field))
            out.write('        return "%s";\n' % field)
            out.write('    else ')
        out.write('\n        return "%s";\n' % struct['fields'][0])
        out.write("}\n")

        out.write("\n")
        out.write("%s::_ %s::fromStr( QString name )\n" % ( struct['name'], struct['name']))
        out.write("{\n")
        out.write("    ")
        for field in struct['fields']:
            field = re.sub("[ ].*$", '', field)
            out.write('if ( name == "%s" )\n' % field)
            out.write('        return %s::%s;\n' % (struct['name'], field))
            out.write('    else ')
        out.write(
            "\n        return %s::%s;\n" % (struct['name'], struct['fields'][0]))
        out.write("}\n")
        out.write("\n")

        out.write("QString %s::toStr( %s::_ name )\n" % (struct['name'], struct['name']))
        out.write("{\n")
        out.write("    ")
        for field in struct['fields']:
            field = re.sub("[ ].*$", '', field)
            out.write('if ( name == %s::%s )\n' % (struct['name'], field))
            out.write('        return "%s";\n' % field)
            out.write('    else ')
        out.write('\n        return "%s";\n' % struct['fields'][0])
        out.write("}\n")
    out.close()


# Ensure we have enough args
if len(sys.argv) < 2:
    print("Usage ./%s output_dir" % sys.argv[0])
    exit(0)

handle( struct_data(), sys.argv[1] )

